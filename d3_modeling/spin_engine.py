"""Spin Doctor engine: precompute what a neighborhood's public 'headline' looks like under every
combination of presentation levers, so the game can run as a static page (no backend).
Levers (index order): denominator(4) x offenses(4) x year(5) x geography(3) x peer group(4);
framing (grade / trend since peak / trend since low) is applied in the game from stored numbers."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from shapely.geometry import shape
from shapely.strtree import STRtree
from features import context, DATA
from offense_groups import offense_group

OUT = Path(__file__).parents[1] / "game" / "data"
YEARS = list(range(2017, 2026))
CHOICE_YEARS = [2025, 2024, 2023, 2022, 2021]
DENOM = ["none (raw counts)", "per resident", "per resident + jobs", "per resident + 2x jobs (\"daytime population\")"]
OFFENSE = ["all offenses", "reliably-reported only", "violent only", "property only"]
GEO = ["this NPA only", "NPA + neighbors", "NPA + neighbors + their neighbors"]
PEER = ["all Charlotte NPAs", "similar-size NPAs", "the 100 highest-count NPAs", "the 100 lowest-count NPAs"]

NEIGHBORHOODS = [
    dict(id="sugar-creek-west", npa=138, name="Sugar Creek Rd / I-85 (NPA 138)",
         blurb="A commercial corridor of motels and retail along West Sugar Creek Road."),
    dict(id="sugar-creek-east", npa=21, name="East Sugar Creek Rd (NPA 21)",
         blurb="The same road, a different boundary: the NoDa-side stretch of Sugar Creek."),
    dict(id="myers-park", npa=392, name="Myers Park (NPA 392)",
         blurb="Tree-lined, historic, high-income residential streets south of Uptown."),
    dict(id="plaza-midwood", npa=315, name="Plaza Midwood (NPA 315)",
         blurb="Mixed bungalows, bars and shops east of Uptown."),
]


def main():
    ctx = context()
    npas = list(ctx.index)
    n, pos = len(npas), {k: i for i, k in enumerate(npas)}
    # ---- counts[offense_set][year] -> vector over NPAs
    raw = pd.read_csv(DATA / "cmpd_npa_year_offense.csv")
    raw = raw[(raw.npa > 0) & (raw.clearance_status != "Unfounded")]
    raw["g"] = raw.nibrs_desc.map(offense_group)
    raw = raw[raw.g != "noncriminal"]
    robbery = raw.nibrs_desc.str.contains("Robbery", case=False)
    masks = {0: np.ones(len(raw), bool), 1: (raw.g == "reliable").values,
             2: ((raw.g == "violent_other") | robbery).values, 3: raw.g.isin(["reliable", "property_other"]).values & ~robbery.values}
    C = np.zeros((4, len(YEARS), n))
    for o, m in masks.items():
        d = raw[m].groupby(["year", "npa"]).n.sum()
        for yi, y in enumerate(YEARS):
            for k, v in d.loc[y].items() if y in d.index.get_level_values(0) else []:
                if k in pos:
                    C[o, yi, pos[k]] = v
    P, J = ctx.population.values, ctx.jobs.values
    DEN = [np.ones(n), P, P + J, P + 2 * J]
    # ---- adjacency
    gj = json.load(open(DATA / "npa.geojson"))
    geoms = {f["properties"]["npa"]: shape(f["geometry"]).buffer(0) for f in gj["features"]}
    g_list = [geoms[k] for k in npas]
    tree = STRtree(g_list)
    A1 = np.eye(n)
    for i, g in enumerate(g_list):
        for j in tree.query(g.buffer(1e-5)):
            if g.intersects(g_list[j]):
                A1[i, j] = 1
    A2 = ((A1 @ A1) > 0).astype(float)
    ADJ = [np.eye(n), A1, A2]

    def scores(d, o, g):  # -> (years, n) score matrix
        num = C[o] @ ADJ[g].T
        den = DEN[d] @ ADJ[g].T
        return num if d == 0 else num / den * 1000

    # honest baseline score vector (per resident, reliable, 2025, own NPA) defines the fixed peer groups
    base = scores(1, 1, 0)[YEARS.index(2025)]
    order = np.argsort(-base)
    top100, bot100 = set(order[:100]), set(order[-100:])

    targets = [pos[h["npa"]] for h in NEIGHBORHOODS]
    arrays = {h["id"]: {"pc": [], "val": [], "peak": [], "low": []} for h in NEIGHBORHOODS}
    for d in range(4):
        for o in range(4):
            for yi_c, yr in enumerate(CHOICE_YEARS):
                for g in range(3):
                    S = scores(d, o, g)
                    s_y = S[YEARS.index(yr)]
                    hist = S[: YEARS.index(yr) + 1]  # years up to the chosen year
                    for h, t in zip(NEIGHBORHOODS, targets):
                        for p in range(4):
                            if p == 0:
                                peers = [i for i in range(n) if i != t]
                            elif p == 1:
                                peers = [i for i in range(n) if i != t and 0.5 * P[t] <= P[i] <= 1.5 * P[t]]
                            elif p == 2:
                                peers = [i for i in top100 if i != t]
                            else:
                                peers = [i for i in bot100 if i != t]
                            pc = 100 * float(np.mean(s_y[peers] < s_y[t])) if peers else 50.0
                            pk, lo = hist[:, t].max(), hist[:, t].min()
                            a = arrays[h["id"]]
                            a["pc"].append(round(pc, 1)); a["val"].append(round(float(s_y[t]), 2))
                            a["peak"].append(round(float((s_y[t] - pk) / pk) if pk else 0.0, 3))
                            a["low"].append(round(float((s_y[t] - lo) / lo) if lo else 0.0, 3))
    for h in NEIGHBORHOODS:
        t = pos[h["npa"]]
        h["population"], h["jobs"] = int(P[t]), int(J[t])
        h["income"] = float(ctx.median_income.iloc[t]) if not np.isnan(ctx.median_income.iloc[t]) else None
        h["data"] = arrays[h["id"]]
    meta = {"levers": [
        {"key": "denominator", "label": "What do we divide by?", "options": DENOM},
        {"key": "offenses", "label": "Which crimes count?", "options": OFFENSE},
        {"key": "year", "label": "Which year?", "options": [str(y) for y in CHOICE_YEARS]},
        {"key": "geography", "label": "How big is 'the neighborhood'?", "options": GEO},
        {"key": "peer", "label": "Compared against...", "options": PEER},
        {"key": "framing", "label": "How is it headlined?", "options": ["letter grade", "% change since peak year", "% change since lowest year"]}],
        "honest": {"denominator": 1, "offenses": 1, "year": 0, "geography": 0, "peer": 0, "framing": 0},
        "n_npas": n, "years": YEARS}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "game_data.json").write_text(json.dumps({"meta": meta, "neighborhoods": NEIGHBORHOODS}, separators=(",", ":")))
    print("wrote", OUT / "game_data.json", (OUT / "game_data.json").stat().st_size // 1024, "KB")
    # quick feasibility report: perceived-safety range by neighborhood
    for h in NEIGHBORHOODS:
        pc = np.array(h["data"]["pc"]); pk = np.array(h["data"]["peak"]); lo = np.array(h["data"]["low"])
        per = np.concatenate([100 - pc, np.clip(50 - 100 * pk, 0, 100), np.clip(50 - 100 * lo, 0, 100)])
        hon = 100 - pc[(((1 * 4 + 1) * 5 + 0) * 3 + 0) * 4 + 0]
        print(f"{h['name']:36s} honest grade-score {hon:5.1f} | perceived-safety range {per.min():5.1f} - {per.max():5.1f}")


if __name__ == "__main__":
    main()
