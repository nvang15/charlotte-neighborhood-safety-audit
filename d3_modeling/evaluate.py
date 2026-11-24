"""D3 model evaluation. One validation method for every model.

Unit: one NPA in one year t. Features use year <= t only. Target: reliably-reported
crime (motor vehicle theft, burglary, robbery) per 1,000 residents in year t+1.

Validation: rolling-origin temporal CV. For target year Y in 2021..2024, fit on rows whose
TARGET year < Y (feature year <= Y-2) and predict feature year Y-1 -> target Y.
Model selection uses CV only. The 2025 target year is scored once at the end.
"""
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from features import build_panel, FEATURES

warnings.filterwarnings("ignore")
OUT = Path(__file__).parent / "results"
(OUT / "figs").mkdir(parents=True, exist_ok=True)
CV_TARGET_YEARS = [2021, 2022, 2023, 2024]
TEST_TARGET_YEAR = 2025
TOP = 0.10  # share of NPAs treated as the "worst-labeled" tier


def poisson_dev(y, mu):
    mu = np.clip(mu, 1e-6, None)
    t = np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0.0)
    return float(2 * np.mean(t - (y - mu)))


class Naive:
    """Rating-site style: rank by last year's raw total count (no denominator). The rate
    prediction is the count rescaled by one train-fit constant, so MAE is comparable."""
    name = "B0 Naive raw count"

    def fit(self, tr):
        self.k = np.median(tr.target_rate / tr.total.clip(lower=1))
        return self

    def predict(self, te):
        return self.k * te.total.values


class EmpiricalBayes:
    """Gamma-Poisson shrinkage of last year's reliable rate toward the city rate."""
    name = "M1 Empirical-Bayes rate"

    def fit(self, tr):
        self.mu = tr.target_count.sum() / (tr.population.sum() / 1000)
        grid = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64]
        errs = [np.mean(np.abs(self._p(tr, a) - tr.target_rate)) for a in grid]
        self.a = grid[int(np.argmin(errs))]
        return self

    def _p(self, d, a):
        expo = d.population.values / 1000
        return (d.reliable.values + a * self.mu) / (expo + a)

    def predict(self, te):
        return self._p(te, self.a)


class PoissonGLM:
    name = "M2 Poisson GLM"

    def _x(self, d):
        x = d[FEATURES].copy()
        for c in ["reliable", "property_other", "violent_other", "discretionary"]:
            x[c] = np.log1p(x[c])
        x["rel_rate_prev"] = np.log1p(x["rel_rate_prev"])
        return x

    def fit(self, tr):
        x = self._x(tr)
        self.m, self.s = x.mean(), x.std().replace(0, 1)
        X = sm.add_constant((x - self.m) / self.s)
        self.res = sm.GLM(tr.target_count.values, X, family=sm.families.Poisson(),
                          offset=np.log(tr.population.values / 1000)).fit(alpha=1e-3, method="IRLS", maxiter=200)
        return self

    def predict(self, te):
        X = sm.add_constant((self._x(te) - self.m) / self.s, has_constant="add")
        return np.exp(X.values @ self.res.params.values)  # rate per 1,000 (offset excluded)


class GBM:
    name = "M3 Gradient boosting (Poisson)"

    def fit(self, tr):
        last = tr.year.max()
        inner_tr, inner_va = tr[tr.year < last], tr[tr.year == last]
        best, self.cfg = np.inf, None
        for lr in (0.03, 0.1):
            for depth in (2, 3):
                m = self._mk(lr, depth).fit(inner_tr[FEATURES], inner_tr.target_rate, sample_weight=inner_tr.population / 1000)
                e = np.mean(np.abs(m.predict(inner_va[FEATURES]) - inner_va.target_rate)) if len(inner_va) else 0
                if e < best:
                    best, self.cfg = e, (lr, depth)
        self.m = self._mk(*self.cfg).fit(tr[FEATURES], tr.target_rate, sample_weight=tr.population / 1000)
        return self

    @staticmethod
    def _mk(lr, depth):
        return HistGradientBoostingRegressor(loss="poisson", learning_rate=lr, max_depth=depth, max_iter=150,
                                             min_samples_leaf=20, l2_regularization=1.0, random_state=0)

    def predict(self, te):
        return self.m.predict(te[FEATURES])


MODELS = [Naive, EmpiricalBayes, PoissonGLM, GBM]


def topset(score, frac=TOP):
    k = max(1, int(round(len(score) * frac)))
    return set(np.argsort(-np.asarray(score))[:k])


def metrics(te, pred, naive_pred):
    y, expo = te.target_rate.values, te.population.values / 1000
    actual_top, pred_top, naive_top = topset(y), topset(pred), topset(naive_pred)
    hit = len(actual_top & pred_top)
    return {
        "mae_rate": float(np.mean(np.abs(pred - y))),
        "poisson_dev": poisson_dev(te.target_count.values, pred * expo),
        "spearman_vs_actual": float(spearmanr(pred, y).correlation),
        "top10_precision": hit / len(pred_top),
        "top10_recall": hit / len(actual_top),
        "spearman_vs_naive": float(spearmanr(pred, naive_pred).correlation),
        "top10_entered_vs_naive": len(pred_top - naive_top),  # NPAs in the tier that naive does not label
    }


def split(panel, target_year):
    d = panel.dropna(subset=["target_rate", "rel_rate_prev"])
    tr = d[d.year + 1 < target_year]
    te = d[d.year + 1 == target_year]
    assert tr.year.max() + 1 < target_year and (te.year + 1 == target_year).all()  # no leakage
    return tr, te


def run_year(panel, target_year):
    tr, te = split(panel, target_year)
    fitted = {M.name: M().fit(tr) for M in MODELS}
    preds = {n: m.predict(te) for n, m in fitted.items()}
    naive = preds[Naive.name]
    rows = [{"model": n, "target_year": target_year, "n_npa": len(te), **metrics(te, p, naive)} for n, p in preds.items()]
    pr = te[["npa", "year", "population", "jobs_per_resident", "target_rate", "pop_tercile", "jobs_tercile", "income_tercile"]].copy()
    pr["target_year"] = target_year
    for n, p in preds.items():
        pr[n] = p
    return rows, pr


def group_errors(pr, models):
    out = []
    for gcol in ["pop_tercile", "jobs_tercile", "income_tercile"]:
        for lvl, g in pr.groupby(gcol, observed=True):
            for n in models:
                y, p = g.target_rate.values, g[n].values
                out.append({"group": gcol, "level": lvl, "model": n, "n": len(g),
                            "mae_rate": np.mean(np.abs(p - y)), "mean_error_pred_minus_actual": np.mean(p - y)})
    return pd.DataFrame(out)


def tier_flag_rates(pr, models):
    """Share of each group's NPAs a model puts in the top-10% tier vs the share that actually is."""
    rows = []
    for ty, d in pr.groupby("target_year"):
        d = d.reset_index(drop=True)
        actual = topset(d.target_rate.values)
        d["actual_top"] = d.index.isin(actual)
        for n in models:
            d["pred_top"] = d.index.isin(topset(d[n].values))
            for gcol in ["jobs_tercile", "pop_tercile", "income_tercile"]:
                for lvl, g in d.groupby(gcol, observed=True):
                    rows.append({"target_year": ty, "model": n, "group": gcol, "level": lvl, "n": len(g),
                                 "flagged": g.pred_top.sum(), "actually_top": g.actual_top.sum()})
    t = pd.DataFrame(rows).groupby(["model", "group", "level"])[["n", "flagged", "actually_top"]].sum().reset_index()
    t["flag_rate"], t["actual_rate"] = t.flagged / t.n, t.actually_top / t.n
    return t


def main():
    panel = build_panel()
    names = [M.name for M in MODELS]
    # ---- cross-validation (model selection happens here only)
    cv_rows, cv_pr = [], []
    for y in CV_TARGET_YEARS:
        r, p = run_year(panel, y)
        cv_rows += r
        cv_pr.append(p)
    cv = pd.DataFrame(cv_rows)
    cv.to_csv(OUT / "metrics_cv_by_fold.csv", index=False)
    summary = cv.groupby("model").mean(numeric_only=True).drop(columns="target_year")
    summary = summary.loc[names]
    summary.to_csv(OUT / "metrics_cv.csv")
    cands = summary.loc[names[1:]]
    selected = cands.poisson_dev.idxmin()
    print("CV mean metrics:\n", summary.round(3).to_string())
    print("\nSELECTED (lowest mean CV Poisson deviance among candidates):", selected)
    pd.Series({"selected": selected, "rule": "lowest mean CV Poisson deviance among M1-M3"}).to_json(OUT / "selected_model.json")

    # ---- error analysis on CV predictions
    cv_pr = pd.concat(cv_pr)
    group_errors(cv_pr, names).to_csv(OUT / "errors_by_group_cv.csv", index=False)
    tier_flag_rates(cv_pr, names).to_csv(OUT / "tier_flags_by_group_cv.csv", index=False)

    # ---- one-time final test on the reserved 2025 target year
    r, test_pr = run_year(panel, TEST_TARGET_YEAR)
    test = pd.DataFrame(r).set_index("model").loc[names]
    test.to_csv(OUT / "metrics_test2025.csv")
    test_pr.to_csv(OUT / "predictions_test2025.csv", index=False)
    group_errors(test_pr, names).to_csv(OUT / "errors_by_group_test2025.csv", index=False)
    print("\nTEST 2025 metrics:\n", test.round(3).to_string())

    # ---- figures
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for a, col, ttl in zip(ax, ["mae_rate", "poisson_dev", "spearman_vs_actual"],
                           ["MAE (rate per 1,000)  lower better", "Poisson deviance  lower better", "Spearman vs actual  higher better"]):
        a.bar(range(4), [summary.loc[n, col] for n in names], alpha=.8, label="CV mean")
        a.bar([i + .35 for i in range(4)], [test.loc[n, col] for n in names], width=.3, alpha=.8, label="2025 test")
        a.set_xticks([i + .17 for i in range(4)], ["B0", "M1", "M2", "M3"])
        a.set_title(ttl, fontsize=9)
    ax[0].legend(fontsize=8)
    plt.tight_layout(); plt.savefig(OUT / "figs/model_comparison.png", dpi=160); plt.close()

    ge = pd.read_csv(OUT / "errors_by_group_cv.csv")
    g = ge[ge.group == "jobs_tercile"].pivot(index="level", columns="model", values="mean_error_pred_minus_actual").loc[["residential", "mixed", "job-heavy"], names]
    g.plot.bar(figsize=(7, 3.6), rot=0); plt.axhline(0, color="k", lw=.8)
    plt.ylabel("mean (predicted - actual) rate per 1,000"); plt.title("Bias by jobs-per-resident group (CV)", fontsize=10)
    plt.legend(fontsize=7); plt.tight_layout(); plt.savefig(OUT / "figs/bias_by_jobs_group.png", dpi=160); plt.close()
    print("\nwrote results/ and figs/")


if __name__ == "__main__":
    main()
