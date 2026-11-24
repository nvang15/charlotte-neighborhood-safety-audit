"""Write tests/golden.json: fixed inputs and the outputs of the saved pipeline.
Postman and the deployed-vs-local check reuse these."""
import json
from pathlib import Path
import pandas as pd
import joblib
from safety_pipeline import RAW_COLUMNS

HERE = Path(__file__).resolve().parent
pipe = joblib.load(HERE / "artifacts/pipeline.joblib")
latest = pd.read_csv(HERE / "artifacts/npa_latest.csv")
cases = [{"label": "illustrative", "input": {"reliable": 180, "property_other": 520, "violent_other": 160, "discretionary": 90,
          "population": 9500, "jobs": 4200, "area_acres": 1300, "reliable_prev": 160}}]
for npa in (138, 21, 392, 315):  # the four NPAs used in the game
    row = latest[latest.npa == npa].iloc[0]
    cases.append({"label": f"NPA {npa} latest inputs",
                  "input": {c: (int(row[c]) if c in ("reliable","property_other","violent_other","discretionary","reliable_prev") else float(row[c])) for c in RAW_COLUMNS}})
for c in cases:
    c["predicted_rate_per_1000"] = round(float(pipe.predict(pd.DataFrame([c["input"]])[RAW_COLUMNS])[0]), 3)
(HERE / "tests/golden.json").write_text(json.dumps({"cases": cases}, indent=2))
print(json.dumps(cases, indent=1)[:900])
