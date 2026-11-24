#!/usr/bin/env bash
# Copy the small precomputed D3 outputs the app reads (no raw incident data).
set -euo pipefail
cd "$(dirname "$0")/.."
R=d3_modeling/results
cp $R/npa_lottery.csv $R/five_scores.csv $R/recipes.csv $R/multiverse_ranks.parquet $R/lottery_summary.json \
   $R/metrics_cv.csv $R/metrics_test2025.csv $R/tier_flags_by_group_cv.csv app/data/
cp d3_modeling/data/npa.geojson app/data/
cp $R/figs/model_comparison.png $R/figs/bias_by_jobs_group.png app/data/
