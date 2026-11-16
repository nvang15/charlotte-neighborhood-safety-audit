"""Label Lottery engine: run every defensible score recipe and record how much each NPA's
rank and 'worst-10%' label depend on the recipe. Rank 1 = highest score (what a rating site
would grade worst). Nothing here says an NPA is unsafe; it measures method sensitivity."""
import itertools
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from features import load_counts, context, build_panel, GROUPS
from evaluate import PoissonGLM, topset

OUT = Path(__file__).parent / "results"
TOP = 0.10
DISPLAY_YEAR = 2025   # latest complete year: the "score" a user would see today
EVAL_YEAR = 2024      # recipes scored on 2024 are checked against 2025 reliable rate (the test year)
EB_STRENGTH = 4.0     # shrinkage strength in 1,000-resident units

DIMS = {
    "denominator": ["none", "residents", "residents + jobs", "residents + half of jobs"],
    "offenses": ["all offenses", "excluding enforcement-driven", "reliably-reported only"],
    "unfounded": ["keep unfounded", "drop unfounded"],
    "window": ["1 year", "3 years"],
    "smoothing": ["raw", "shrunk toward city rate"],
}
OFFENSE_SETS = {"all offenses": GROUPS, "excluding enforcement-driven": ["reliable", "property_other", "violent_other"],
                "reliably-reported only": ["reliable"]}


def recipes():
    out = []
    for combo in itertools.product(*DIMS.values()):
        r = dict(zip(DIMS, combo))
        if r["denominator"] == "none" and r["smoothing"] != "raw":
            continue  # shrinkage needs a denominator
        out.append(r)
    return out


def score(r, year, counts_by_unf, ctx):
    c = counts_by_unf[r["unfounded"]]
    years = [year] if r["window"] == "1 year" else [year - 2, year - 1, year]
    cc = c[c.index.get_level_values("year").isin(years)].groupby("npa")[OFFENSE_SETS[r["offenses"]]].sum().sum(axis=1) / len(years)
    cc = cc.reindex(ctx.index, fill_value=0.0)
    if r["denominator"] == "none":
        return cc
    denom = {"residents": ctx.population, "residents + jobs": ctx.population + ctx.jobs,
             "residents + half of jobs": ctx.population + 0.5 * ctx.jobs}[r["denominator"]]
    expo = denom / 1000
    if r["smoothing"] == "raw":
        return cc / expo
    mu = cc.sum() / expo.sum()
    return (cc + EB_STRENGTH * mu) / (expo + EB_STRENGTH)


def tier_ranks(s):
    return s.rank(ascending=False, method="first")


def main():
    ctx = context()
    counts = {"keep unfounded": load_counts(drop_unfounded=False), "drop unfounded": load_counts(drop_unfounded=True)}
    recs = recipes()
    n = len(ctx)
    k = int(round(n * TOP))
    panel = build_panel()
    actual_2025 = panel[panel.year == 2025].set_index("npa").reliable_rate.reindex(ctx.index)

    ranks, recipe_rows = {}, []
    for i, r in enumerate(recs):
        rid = f"R{i:02d}"
        rk = tier_ranks(score(r, DISPLAY_YEAR, counts, ctx))
        ranks[rid] = rk
        s_eval = score(r, EVAL_YEAR, counts, ctx)
        top_eval = set(s_eval.nlargest(k).index)
        top_act = set(actual_2025.nlargest(k).index)
        recipe_rows.append({"recipe_id": rid, **r,
                            "spearman_vs_2025_reliable_rate": spearmanr(s_eval, actual_2025).correlation,
                            "top10_overlap_with_2025_reliable_top10": len(top_eval & top_act) / k})
    R = pd.DataFrame(ranks)  # npa x recipe
    recipes_df = pd.DataFrame(recipe_rows)
    R.T.to_parquet(OUT / "multiverse_ranks.parquet")
    recipes_df.to_csv(OUT / "recipes.csv", index=False)

    in_top = (R <= k)
    # which choice moves each NPA's rank most: avg |rank diff| between recipes that differ only in that choice
    infl = {}
    rr = recipes_df.set_index("recipe_id")
    for dim in DIMS:
        others = [d for d in DIMS if d != dim]
        diffs = []
        for _, g in rr.groupby(others):
            ids = list(g.index)
            for a, b in itertools.combinations(ids, 2):
                diffs.append((R[a] - R[b]).abs())
        infl[dim] = sum(diffs) / max(len(diffs), 1)
    infl = pd.DataFrame(infl)

    lot = pd.DataFrame({"npa": R.index, "p_worst10": in_top.mean(axis=1).values,
                        "rank_best": R.min(axis=1).values, "rank_median": R.median(axis=1).values,
                        "rank_worst": R.max(axis=1).values, "n_recipes": len(recs)})
    lot["most_influential_choice"] = infl.idxmax(axis=1).values
    lot["influence_rank_points"] = infl.max(axis=1).values
    lot["ever_worst10"] = (in_top.any(axis=1)).values
    lot["always_worst10"] = (in_top.all(axis=1)).values
    lot = lot.merge(ctx.reset_index()[["npa", "population", "jobs", "median_income", "income_tercile", "jobs_tercile", "pop_tercile"]], on="npa")
    lot.to_csv(OUT / "npa_lottery.csv", index=False)

    # five-score slider (proposal): naive -> per resident -> daytime -> reliable -> model
    five = {}
    base = dict(unfounded="drop unfounded", window="1 year", smoothing="raw")
    steps = {"1 Naive raw count": dict(denominator="none", offenses="all offenses"),
             "2 Per resident": dict(denominator="residents", offenses="all offenses"),
             "3 Daytime-adjusted": dict(denominator="residents + half of jobs", offenses="all offenses"),
             "4 Reliably-reported only": dict(denominator="residents + half of jobs", offenses="reliably-reported only")}
    for name, st in steps.items():
        five[name] = score({**base, **st}, DISPLAY_YEAR, counts, ctx)
    d = panel.dropna(subset=["target_rate", "rel_rate_prev"])
    model = PoissonGLM().fit(d[d.year <= DISPLAY_YEAR - 1])
    cur = panel[(panel.year == DISPLAY_YEAR)].set_index("npa").loc[ctx.index].reset_index()
    five["5 Model (Poisson GLM)"] = pd.Series(model.predict(cur), index=ctx.index)
    F = pd.DataFrame(five)
    fr = F.rank(ascending=False, method="first")
    fout = pd.concat([F.add_suffix(" | score"), fr.add_suffix(" | rank")], axis=1).reset_index()
    fout.to_csv(OUT / "five_scores.csv", index=False)

    # headline numbers
    ever, always = int(lot.ever_worst10.sum()), int(lot.always_worst10.sum())
    summ = {"n_npa": n, "n_recipes": len(recs), "tier_size": k, "ever_worst10": ever, "always_worst10": always,
            "flip_flop": int(((lot.p_worst10 > 0) & (lot.p_worst10 < 1)).sum()),
            "median_rank_range": float((lot.rank_worst - lot.rank_best).median()),
            "recipe_spearman_vs_2025_min": float(recipes_df.spearman_vs_2025_reliable_rate.min()),
            "recipe_spearman_vs_2025_max": float(recipes_df.spearman_vs_2025_reliable_rate.max())}
    (OUT / "lottery_summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))
    print(lot.most_influential_choice.value_counts())


if __name__ == "__main__":
    main()
