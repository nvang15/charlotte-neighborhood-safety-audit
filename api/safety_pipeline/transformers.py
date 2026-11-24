"""Custom transformer for the NPA-year reliably-reported-crime model.

It turns the raw facts a caller can know at prediction time (last year's offense
counts for one NPA, its size and job base, and the year before's reliable count)
into the nine model features chosen in D3 (`d3_modeling/features.py`, `evaluate.py`).
Every input describes year t or earlier; the target is year t+1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

# Raw columns a caller supplies (one row = one NPA in one year t).
RAW_COLUMNS = [
    "reliable",            # year-t motor vehicle theft + burglary + robbery reports
    "property_other",      # year-t other property offenses
    "violent_other",       # year-t other violent offenses
    "discretionary",       # year-t offenses driven by police activity (e.g. drugs, weapons)
    "population",          # residents (QOL profile)
    "jobs",                # jobs located in the NPA (QOL profile)
    "area_acres",          # NPA land area
    "reliable_prev",       # year t-1 reliable count (same definition as `reliable`)
]

FEATURE_NAMES = [
    "log1p_reliable", "log1p_property_other", "log1p_violent_other", "log1p_discretionary",
    "discretionary_share", "log_population", "log_jobs_per_resident", "log_density",
    "log1p_reliable_rate_prev",
]


class CrimeFeatureBuilder(BaseEstimator, TransformerMixin):
    """Raw NPA-year facts -> model features.

    Learned state (set in `fit`): the training row count, the per-feature training
    minimum and maximum (`feature_range_`), and the column order. At transform time
    inputs are checked for missing columns and impossible values, and features that
    fall outside the training range are counted in `n_out_of_range_` for the caller
    to report; values are never clipped, so the model sees what was sent.
    """

    def fit(self, X, y=None):
        df = self._frame(X)
        F = self._features(df)
        self.feature_names_in_ = np.array(RAW_COLUMNS)
        self.n_features_in_ = len(RAW_COLUMNS)
        self.n_train_rows_ = len(df)
        self.feature_range_ = {n: (float(F[n].min()), float(F[n].max())) for n in FEATURE_NAMES}
        return self

    def transform(self, X):
        check_is_fitted(self, "feature_range_")
        F = self._features(self._frame(X))
        return F[FEATURE_NAMES].to_numpy(dtype=float)

    def get_feature_names_out(self, input_features=None):
        return np.array(FEATURE_NAMES)

    def out_of_range(self, X) -> list[str]:
        """Feature names (for the first row) outside the training min/max."""
        check_is_fitted(self, "feature_range_")
        F = self._features(self._frame(X)).iloc[0]
        return [n for n in FEATURE_NAMES if not (self.feature_range_[n][0] <= F[n] <= self.feature_range_[n][1])]

    # ---- internals
    @staticmethod
    def _frame(X) -> pd.DataFrame:
        df = X if isinstance(X, pd.DataFrame) else pd.DataFrame(X, columns=RAW_COLUMNS)
        missing = [c for c in RAW_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"missing columns: {missing}")
        df = df[RAW_COLUMNS].astype(float)
        if df.isna().any().any():
            raise ValueError("NaN values are not allowed")
        counts = ["reliable", "property_other", "violent_other", "discretionary", "jobs", "reliable_prev"]
        if (df[counts] < 0).any().any():
            raise ValueError("counts and jobs must be >= 0")
        if (df[["population", "area_acres"]] <= 0).any().any():
            raise ValueError("population and area_acres must be > 0")
        return df

    @staticmethod
    def _features(df: pd.DataFrame) -> pd.DataFrame:
        total = df[["reliable", "property_other", "violent_other", "discretionary"]].sum(axis=1)
        out = pd.DataFrame(index=df.index)
        out["log1p_reliable"] = np.log1p(df.reliable)
        out["log1p_property_other"] = np.log1p(df.property_other)
        out["log1p_violent_other"] = np.log1p(df.violent_other)
        out["log1p_discretionary"] = np.log1p(df.discretionary)
        out["discretionary_share"] = df.discretionary / total.clip(lower=1)
        out["log_population"] = np.log(df.population)
        out["log_jobs_per_resident"] = np.log1p(df.jobs / df.population)
        out["log_density"] = np.log(df.population / df.area_acres)
        out["log1p_reliable_rate_prev"] = np.log1p(df.reliable_prev / df.population * 1000)
        return out
