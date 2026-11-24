"""Fit and save the D4 pipeline: CrimeFeatureBuilder -> StandardScaler -> PoissonRegressor.

Same model family and training window as the D3 selection (M2 Poisson GLM, rows whose
TARGET year is <= 2024). The 2025 target year stays untouched for the D6 final test; this
script never scores it. Parity with the D3 statsmodels model is checked on the 2024 CV fold.

Run from the repo root:   .venv/bin/python api/train.py
"""
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "d3_modeling"))

from safety_pipeline import RAW_COLUMNS, CrimeFeatureBuilder  # noqa: E402
from features import build_panel  # noqa: E402
import evaluate  # noqa: E402  (D3 code, for the parity check only)

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
FINAL_TARGET_CUTOFF = 2025  # rows with target year >= 2025 are never used for fitting here


def make_pipeline() -> Pipeline:
    return Pipeline([
        ("features", CrimeFeatureBuilder()),
        ("scale", StandardScaler()),
        # alpha=0: unpenalised, matching the D3 statsmodels GLM. Fitting the rate with
        # sample_weight = residents/1000 is the same likelihood as counts with a log-exposure offset.
        ("glm", PoissonRegressor(alpha=0.0, max_iter=1000)),
    ])


def raw_frame(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.sort_values(["npa", "year"]).copy()
    p["reliable_prev"] = p.groupby("npa").reliable.shift(1)
    return p


def fit_on(rows: pd.DataFrame) -> Pipeline:
    pipe = make_pipeline()
    pipe.fit(rows[RAW_COLUMNS], rows.target_rate, glm__sample_weight=rows.population / 1000)
    return pipe


def training_rows(p: pd.DataFrame, target_year_exclusive: int) -> pd.DataFrame:
    d = p.dropna(subset=["target_rate", "rel_rate_prev", "reliable_prev"])
    return d[d.year + 1 < target_year_exclusive]


def main():
    panel = raw_frame(build_panel())

    # ---- parity check vs the D3 statsmodels GLM on the 2024 CV fold (no 2025 data touched)
    tr, te = evaluate.split(panel, 2024)
    tr_s = tr.dropna(subset=["reliable_prev"])
    pipe_cv = fit_on(tr_s)
    sk = pipe_cv.predict(te[RAW_COLUMNS])
    sm = evaluate.PoissonGLM().fit(tr).predict(te)
    parity = {"fold_target_year": 2024, "n": int(len(te)),
              "max_abs_diff_rate": float(np.max(np.abs(sk - sm))),
              "spearman": float(pd.Series(sk).corr(pd.Series(sm), method="spearman")),
              "mae_sklearn": float(np.mean(np.abs(sk - te.target_rate))),
              "mae_statsmodels": float(np.mean(np.abs(sm - te.target_rate)))}
    print("parity vs D3 statsmodels (2024 fold):", json.dumps(parity, indent=1))

    # ---- final frozen fit: target years <= 2024  (feature years <= 2023)
    rows = training_rows(panel, FINAL_TARGET_CUTOFF)
    assert (rows.year + 1).max() <= 2024
    pipe = fit_on(rows)
    joblib.dump(pipe, ART / "pipeline.joblib", compress=3)

    # ---- lookup table the API serves to the frontend: latest observed year -> next-year outlook
    latest_year = int(panel.year.max())
    latest = panel[panel.year == latest_year].dropna(subset=["reliable_prev"])[["npa"] + RAW_COLUMNS].copy()
    latest["npa"] = latest.npa.astype(int)
    latest["feature_year"] = latest_year
    latest.to_csv(ART / "npa_latest.csv", index=False)
    ref = pipe.predict(latest[RAW_COLUMNS])
    np.save(ART / "reference_predictions.npy", np.sort(ref))

    glm = pipe.named_steps["glm"]
    meta = {
        "model": "Poisson regression on log-rate (M2 in D3), sklearn Pipeline",
        "steps": [s for s, _ in pipe.steps],
        "custom_transformer": "safety_pipeline.CrimeFeatureBuilder",
        "target": "reliably-reported crime rate per 1,000 residents in year t+1 "
                  "(motor vehicle theft, burglary, robbery)",
        "inputs": RAW_COLUMNS,
        "training": {"n_rows": int(len(rows)), "n_npas": int(rows.npa.nunique()),
                     "feature_years": [int(rows.year.min()), int(rows.year.max())],
                     "target_years": [int(rows.year.min()) + 1, int(rows.year.max()) + 1],
                     "final_test_target_year_reserved": 2025},
        "latest_feature_year": latest_year,
        "coefficients_standardised": dict(zip(pipe.named_steps["features"].get_feature_names_out().tolist(),
                                              np.round(glm.coef_, 4).tolist())),
        "intercept": round(float(glm.intercept_), 4),
        "parity_vs_d3_statsmodels": parity,
        "d3_reference_metrics": "d3_modeling/results/metrics_cv.csv (selection) and the D3 note",
        "library_versions": {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
                             "numpy": np.__version__, "pandas": pd.__version__,
                             "scipy": scipy.__version__, "joblib": joblib.__version__},
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_sha256": hashlib.sha256((ART / "pipeline.joblib").read_bytes()).hexdigest(),
        "limitations": [
            "Predicts reported crime, not actual crime or safety.",
            "NPA population and jobs are single QOL snapshots, not year-specific.",
            "NPAs with population under 500 are excluded; inputs below 500 are rejected.",
            "Prediction does not establish causation.",
        ],
    }
    (ART / "metadata.json").write_text(json.dumps(meta, indent=2))
    print("saved:", [f.name for f in ART.iterdir()], "| rows", len(rows), "| latest year", latest_year)


if __name__ == "__main__":
    main()
