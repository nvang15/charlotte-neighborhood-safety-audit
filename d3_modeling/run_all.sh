#!/usr/bin/env bash
# Reproduce D3 from scratch (needs network for the two fetch steps; ~5 min).
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install -q -r requirements.txt
python fetch_context.py     # NPA population, jobs, income, polygons (City QOL service)
python fetch_cmpd.py        # NPA x year x offense x clearance counts (CMPD open layer)
python evaluate.py          # CV, model selection, one-time 2025 test, error analysis, figures
python multiverse.py        # Label Lottery: 84 score recipes per NPA
python spin_engine.py       # Spin Doctor game data -> game/data/game_data.json
