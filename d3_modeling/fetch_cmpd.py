"""Fetch NPA x year x offense x clearance counts from CMPD's open ArcGIS layer using
server-side grouped statistics (no incident-level rows are downloaded)."""
import json
import time
from pathlib import Path
import pandas as pd
import requests

URL = "https://gis.charlottenc.gov/arcgis/rest/services/CMPD/CMPDIncidents/MapServer/0/query"
DATA = Path(__file__).parent / "data"
YEARS = range(2017, 2026)  # 2026 is incomplete and excluded
STATS = json.dumps([{"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"}])


def get_with_retry(params, tries=5):
    for i in range(tries):
        try:
            r = requests.get(URL, params=params, timeout=300)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            print(f"retry {i + 1}/{tries}: {type(exc).__name__}", flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError("CMPD service did not respond; rerun to resume from cached years")


def fetch_range(year, lo, hi):
    """Grouped counts for NPA in [lo, hi). No offset/order (slow and unstable on this
    service): if a range hits the 2,500-group cap, split it in half and retry."""
    params = {"where": f"YEAR='{year}' AND NPA>={lo} AND NPA<{hi}", "outStatistics": STATS,
              "groupByFieldsForStatistics": "NPA,HIGHEST_NIBRS_DESCRIPTION,CLEARANCE_STATUS", "f": "json"}
    d = get_with_retry(params)
    if "error" in d:
        raise RuntimeError(d["error"])
    if d.get("exceededTransferLimit"):
        if hi - lo <= 1:
            raise RuntimeError(f"NPA {lo} year {year} exceeds transfer limit")
        mid = (lo + hi) // 2
        return fetch_range(year, lo, mid) + fetch_range(year, mid, hi)
    return [f["attributes"] for f in d["features"]]


def fetch_year(year):
    cache = DATA / f"_cache_{year}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    rows = fetch_range(year, -1000, 100000)
    df = pd.DataFrame(rows)
    df["year"] = year
    df.to_csv(cache, index=False)
    print(f"year {year}: {len(df)} groups", flush=True)
    return df


def main():
    DATA.mkdir(exist_ok=True)
    df = pd.concat([fetch_year(y) for y in YEARS], ignore_index=True)
    df.columns = ["npa", "nibrs_desc", "clearance_status", "n", "year"]
    df.to_csv(DATA / "cmpd_npa_year_offense.csv", index=False)
    tot = df.groupby("year")["n"].sum()
    print("fetched totals by year:\n", tot)
    d2 = Path(__file__).parents[1] / "dashboard/data/cmpd_npa_year_counts.csv"
    if d2.exists():
        ref = pd.read_csv(d2).groupby("year")["report_count"].sum()
        cmp = pd.DataFrame({"fetched": tot, "d2_reference": ref})
        cmp["diff"] = cmp.fetched - cmp.d2_reference
        print("\nreconciliation with D2 aggregates (positive diff = newer rows or NPA<=0/null):\n", cmp)


if __name__ == "__main__":
    main()
