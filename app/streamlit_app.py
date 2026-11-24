"""Label Lottery: how much does a neighborhood's 'worst-10%' label depend on the analyst's choices?
Reads only small precomputed NPA-level outputs (app/data). No incident-level data."""
import json
from pathlib import Path
import altair as alt
import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

D = Path(__file__).parent / "data"
st.set_page_config(page_title="Label Lottery: Charlotte", layout="wide")
CHOICES = ["denominator", "offenses", "unfounded", "window", "smoothing"]
FIVE = ["1 Naive raw count", "2 Per resident", "3 Daytime-adjusted", "4 Reliably-reported only", "5 Model (Poisson GLM)"]
FIVE_NOTE = {
    FIVE[0]: "Total reported incidents. What a simple rating site might rank by.",
    FIVE[1]: "Same counts, divided by residents.",
    FIVE[2]: "Divides by residents plus half of the area's jobs, so job-heavy areas are not penalized for commuter traffic.",
    FIVE[3]: "Only motor vehicle theft, burglary and robbery (crimes victims almost always report), per resident-and-job exposure.",
    FIVE[4]: "Poisson model of next-year reliably-reported crime rate, fit on earlier years (the selected D3 model).",
}


@st.cache_data
def load():
    lot = pd.read_csv(D / "npa_lottery.csv")
    five = pd.read_csv(D / "five_scores.csv")
    rec = pd.read_csv(D / "recipes.csv")
    ranks = pd.read_parquet(D / "multiverse_ranks.parquet")  # recipes x npa
    ranks.columns = ranks.columns.astype(int)
    geo = json.loads((D / "npa.geojson").read_text())
    summ = json.loads((D / "lottery_summary.json").read_text())
    return lot, five, rec, ranks, geo, summ


lot, five, rec, ranks, geo, summ = load()
K = summ["tier_size"]


def recipe_text(row):
    return " · ".join(f"{c}: {row[c]}" for c in CHOICES)


def color_scale(v):  # 0..1 -> light-to-dark blue-violet (sequential; not a good/bad palette)
    v = float(np.clip(v, 0, 1))
    a, b = np.array([237, 241, 250]), np.array([55, 30, 120])
    return [int(x) for x in (a + (b - a) * v)] + [200]


def map_view(values, tooltip_fn, highlight=None):
    feats = []
    for f in geo["features"]:
        npa = f["properties"]["npa"]
        if npa not in values.index:
            continue
        v = values[npa]
        props = {"npa": int(npa), "fill": color_scale(v) if not np.isnan(v) else [220, 220, 220, 120], "tip": tooltip_fn(npa)}
        if highlight is not None and npa == highlight:
            props["fill"] = [255, 160, 0, 255]
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": props})
    layer = pdk.Layer("GeoJsonLayer", {"type": "FeatureCollection", "features": feats}, get_fill_color="properties.fill",
                      get_line_color=[255, 255, 255, 150], line_width_min_pixels=0.5, pickable=True, stroked=True, filled=True)
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=pdk.ViewState(latitude=35.23, longitude=-80.84, zoom=10.1),
                             map_style="light", tooltip={"text": "{tip}"}), width="stretch", height=520)


st.title("The Label Lottery")
st.caption("Rated for Whom? Auditing neighborhood safety scores in Charlotte · aggregated CMPD reports by Neighborhood Profile Area (NPA), 2017–2025")
st.info("This app measures **how much a label depends on method choices**. It does not say any neighborhood is safe or unsafe, "
        "and police-reported counts are not a measure of all crime. NPA boundaries may not match everyday neighborhoods.")

tab1, tab2, tab3, tab4 = st.tabs(["The Lottery", "Five Scores", "Neighborhood card", "Model check"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric(f"NPAs labeled worst-10% by at least one of {summ['n_recipes']} recipes", summ["ever_worst10"])
    c2.metric("…by every recipe", summ["always_worst10"])
    c3.metric("Median gap between best and worst rank", f"{summ['median_rank_range']:.0f} of {summ['n_npa']}")
    st.markdown(f"Each recipe is a defensible way to score 2025 reports (what to divide by, which offenses to count, "
                f"how many years, whether to smooth). The {K} highest-scoring NPAs get the “worst” label. "
                f"**{summ['flip_flop']} NPAs are labeled worst-10% under some recipes and not others.**")
    mode = st.radio("Map", ["Lottery odds (share of recipes that label the NPA worst-10%)", "Spin: one random recipe"], horizontal=True)
    if mode.startswith("Lottery"):
        vals = lot.set_index("npa").p_worst10
        lk = lot.set_index("npa")
        map_view(vals, lambda n: f"NPA {n}: labeled worst-10% in {vals[n]:.0%} of recipes; rank {lk.rank_best[n]:.0f}–{lk.rank_worst[n]:.0f}")
        st.caption("Darker = labeled worst-10% by more recipes. Hover an area for details.")
    else:
        if "spin" not in st.session_state:
            st.session_state.spin = 0
        if st.button("Spin the wheel"):
            st.session_state.spin = int(np.random.randint(len(rec)))
        r = rec.iloc[st.session_state.spin]
        rk = ranks.iloc[st.session_state.spin]
        vals = (rk <= K).astype(float)
        st.markdown(f"**Recipe {r.recipe_id}:** {recipe_text(r)}")
        map_view(vals, lambda n: f"NPA {n}: rank {rk[n]:.0f} under this recipe")
        st.caption(f"Dark = labeled worst-10% under this recipe ({int(vals.sum())} NPAs). Spin again and watch the map change.")
    st.subheader("Which choice changes labels most?")
    cnt = lot.most_influential_choice.value_counts().rename_axis("choice").reset_index(name="NPAs")
    st.altair_chart(alt.Chart(cnt).mark_bar().encode(x=alt.X("NPAs:Q"), y=alt.Y("choice:N", sort="-x", title=None), tooltip=["choice", "NPAs"]).properties(height=160), width="stretch")
    st.caption("For each NPA, the choice whose flip moves its rank the most. Whether to divide by residents (and by what) and whether to smooth small areas matter most.")

with tab2:
    step = st.select_slider("Correction step", options=FIVE, value=FIVE[0])
    st.write(FIVE_NOTE[step])
    fr = five.set_index("npa")
    rk = fr[f"{step} | rank"]
    base = fr[f"{FIVE[0]} | rank"]
    top = (rk <= K).astype(float)
    entered = int(((rk <= K) & (base > K)).sum())
    left = int(((rk > K) & (base <= K)).sum())
    a, b, c = st.columns(3)
    a.metric("NPAs in worst-10% tier", int(top.sum()))
    b.metric("Entered tier vs naive", entered)
    c.metric("Left tier vs naive", left)
    map_view(top, lambda n: f"NPA {n}: rank {rk[n]:.0f} · naive rank {base[n]:.0f}")
    st.caption("Dark = in the top-10% tier of this score. Slide to see which areas change at each correction.")

with tab3:
    npa = int(st.selectbox("Neighborhood Profile Area", [f"NPA {n}" for n in sorted(lot.npa)]).split()[1])
    row = lot.set_index("npa").loc[npa]
    a, b, c = st.columns(3)
    a.metric("Labeled worst-10%", f"{row.p_worst10:.0%} of recipes")
    b.metric("Rank range", f"{row.rank_best:.0f} – {row.rank_worst:.0f}")
    c.metric("Most influential choice", row.most_influential_choice)
    st.caption(f"Residents (2020): {row.population:,.0f} · jobs (2022): {row.jobs:,.0f} · median household income: ${row.median_income:,.0f}")
    pr = pd.DataFrame({"rank": ranks[npa].values, "recipe_id": rec.recipe_id})
    sel = st.selectbox("Color by choice", CHOICES[:2] + CHOICES[3:], index=0)
    pr[sel] = rec[sel].values
    chart = alt.Chart(pr).mark_circle(size=70, opacity=0.75).encode(
        x=alt.X("rank:Q", title=f"Rank among {summ['n_npa']} NPAs (1 = highest score)", scale=alt.Scale(domain=[1, summ["n_npa"]])),
        y=alt.Y("jitter:Q", axis=None), color=alt.Color(f"{sel}:N"), tooltip=["recipe_id", "rank", sel]
    ).transform_calculate(jitter="random()").properties(height=150)
    rule = alt.Chart(pd.DataFrame({"x": [K]})).mark_rule(strokeDash=[4, 4]).encode(x="x:Q")
    st.altair_chart(chart + rule, width="stretch")
    st.caption(f"Each dot is one recipe's rank for this NPA. Left of the dashed line = inside the worst-{K} tier.")

with tab4:
    st.markdown("Models predict next year's reliably-reported crime (motor vehicle theft, burglary, robbery) per 1,000 residents. "
                "Fit on earlier years only; 2025 was scored once after model selection.")
    cv = pd.read_csv(D / "metrics_cv.csv").round(3)
    te = pd.read_csv(D / "metrics_test2025.csv").round(3)
    st.subheader("2025 test"); st.dataframe(te[["model", "mae_rate", "poisson_dev", "spearman_vs_actual", "top10_precision"]], hide_index=True)
    st.subheader("Cross-validation mean (2021–2024)"); st.dataframe(cv[["model", "mae_rate", "poisson_dev", "spearman_vs_actual", "top10_precision"]], hide_index=True)
    st.image(str(D / "model_comparison.png")); st.image(str(D / "bias_by_jobs_group.png"))
    st.markdown("**Recipes vs the same 2025 outcome:** the 84 recipes' rank correlations with the 2025 reliably-reported rate range from "
                f"{summ['recipe_spearman_vs_2025_min']:.2f} to {summ['recipe_spearman_vs_2025_max']:.2f}. Many look accurate while giving different labels, "
                "which is why accuracy alone does not make a score the right one.")
    st.caption("Limits: no ground truth for crime; reliable-crime grouping follows national victim-survey patterns; jobs miss visitors; one boundary set and a single 2020 population estimate.")
