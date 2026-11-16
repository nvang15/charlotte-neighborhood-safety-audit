"""Fetch NPA context (population, jobs, income, housing, polygons) from Charlotte's
Quality of Life (QOL) profile service. One boundary set is used for every year."""
import json
from pathlib import Path
import pandas as pd
import requests

BASE = "https://gis.charlottenc.gov/arcgis/rest/services/QOL/Quality_of_Life_Latest_Profile_Data/MapServer"
DATA = Path(__file__).parent / "data"
# layer id -> (output column, field to use)
LAYERS = {
    2: ("population", "Val_Raw"),        # total population estimate (2020)
    18: ("jobs", "Val_Raw"),             # number of jobs by workplace (2022): daytime-population proxy
    17: ("median_income", "Val_Norm"),   # median household income
    67: ("housing_units", "Val_Raw"),
    74: ("occupancy_pct", "Val_Norm"),
    14: ("commercial_space", "Val_Raw"),
}


def query(layer, geometry=False):
    out = []
    offset = 0
    while True:
        params = {"where": "1=1", "outFields": "NPA,Year,Val_Raw,Val_Norm,Shape.STArea()", "returnGeometry": str(geometry).lower(),
                  "resultOffset": offset, "resultRecordCount": 200, "f": "geojson" if geometry else "json", "outSR": 4326}
        r = requests.get(f"{BASE}/{layer}/query", params=params, timeout=120)
        r.raise_for_status()
        d = r.json()
        feats = d["features"]
        out.extend(feats)
        if len(feats) < 200 and not d.get("exceededTransferLimit"):
            break
        offset += len(feats)
    return out


def main():
    DATA.mkdir(exist_ok=True)
    frames = []
    for layer, (col, field) in LAYERS.items():
        feats = query(layer)
        df = pd.DataFrame([f["attributes"] for f in feats])
        df = df.rename(columns={"NPA": "npa"})
        s = df.groupby("npa")[field].first().rename(col)
        frames.append(s)
        print(f"layer {layer} {col}: {s.notna().sum()} NPAs with values")
        if layer == 2:
            area = df.groupby("npa")["Shape.STArea()"].first().rename("area_sqm")
            frames.append(area)
    ctx = pd.concat(frames, axis=1).reset_index()
    ctx["area_acres"] = ctx["area_sqm"] / 4046.856
    ctx.to_csv(DATA / "npa_context.csv", index=False)
    print(ctx.describe().T[["count", "min", "50%", "max"]])
    geo = query(2, geometry=True)
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": f["geometry"], "properties": {"npa": f["properties"]["NPA"]}} for f in geo]}
    (DATA / "npa.geojson").write_text(json.dumps(gj))
    print("polygons:", len(gj["features"]))


if __name__ == "__main__":
    main()
