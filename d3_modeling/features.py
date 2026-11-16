"""NPA x year panel. Features for year t use only year-t (or earlier) information;
the target is year t+1's reliably-reported crime rate per 1,000 residents."""
from pathlib import Path
import numpy as np
import pandas as pd
from offense_groups import offense_group

DATA = Path(__file__).parent / "data"
GROUPS = ["reliable", "property_other", "violent_other", "discretionary"]


def load_counts(drop_unfounded=True):
    df = pd.read_csv(DATA / "cmpd_npa_year_offense.csv")
    df = df[df.npa > 0]
    df["group"] = df.nibrs_desc.map(offense_group)
    df = df[df.group != "noncriminal"]
    if drop_unfounded:
        df = df[df.clearance_status != "Unfounded"]
    return df.groupby(["npa", "year", "group"]).n.sum().unstack("group", fill_value=0).reindex(columns=GROUPS, fill_value=0)


def context():
    c = pd.read_csv(DATA / "npa_context.csv").set_index("npa")
    c = c[(c.population >= 500)]  # rates on tiny populations are not meaningful; documented limit
    c["jobs_per_resident"] = c.jobs / c.population
    c["income_tercile"] = pd.qcut(c.median_income.where(c.median_income > 0), 3, labels=["low", "mid", "high"])
    c["pop_tercile"] = pd.qcut(c.population, 3, labels=["small", "mid", "large"])
    c["jobs_tercile"] = pd.qcut(c.jobs_per_resident, 3, labels=["residential", "mixed", "job-heavy"])
    return c


def build_panel():
    counts = load_counts()
    ctx = context()
    years = sorted(counts.index.get_level_values("year").unique())
    idx = pd.MultiIndex.from_product([ctx.index, years], names=["npa", "year"])
    p = counts.reindex(idx, fill_value=0).reset_index().merge(ctx.reset_index(), on="npa")
    p["total"] = p[GROUPS].sum(axis=1)
    p["reliable_rate"] = p.reliable / p.population * 1000
    p["total_rate"] = p.total / p.population * 1000
    p["disc_share"] = p.discretionary / p.total.clip(lower=1)
    p = p.sort_values(["npa", "year"])
    # prior-year lags (year t features -> predict t+1)
    p["target_rate"] = p.groupby("npa").reliable_rate.shift(-1)
    p["target_count"] = p.groupby("npa").reliable.shift(-1)
    p["rel_rate_lag1"] = p.reliable_rate
    p["rel_rate_prev"] = p.groupby("npa").reliable_rate.shift(1)
    p["log_pop"] = np.log(p.population)
    p["log_jobs_per_res"] = np.log1p(p.jobs_per_resident)
    p["log_density"] = np.log(p.population / p.area_acres)
    return p


FEATURES = ["reliable", "property_other", "violent_other", "discretionary", "disc_share",
            "log_pop", "log_jobs_per_res", "log_density", "rel_rate_prev"]

if __name__ == "__main__":
    p = build_panel()
    print(p.shape, p.npa.nunique(), "NPAs")
    print(p.groupby("year")[["reliable", "total"]].sum())
