"""Check that the deployed Modal API returns the same outputs as the local saved pipeline.

For every case in tests/golden.json it compares three numbers:
  - the fixture value (written by make_golden.py from the saved artifact),
  - a fresh local prediction from artifacts/pipeline.joblib,
  - the deployed API's POST /predict response.
It also checks the deployed health, pipeline-info, 422 and 404 behaviour, and writes
verify_deployed.json as evidence. (503 is tested locally only; see tests/test_api.py.)

Run from the repo root:
    PYTHONPATH=api .venv/bin/python api/verify_deployed.py [API_URL]
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import joblib
import pandas as pd

from safety_pipeline import RAW_COLUMNS

HERE = Path(__file__).resolve().parent
DEFAULT_URL = "https://jconrad8--charlotte-npa-crime-rate-api-serve.us-east.modal.run"
TOL = 1e-3  # API rounds rates to 3 decimals


def main(url: str) -> int:
    url = url.rstrip("/")
    pipe = joblib.load(HERE / "artifacts/pipeline.joblib")
    meta = json.loads((HERE / "artifacts/metadata.json").read_text())
    cases = json.loads((HERE / "tests/golden.json").read_text())["cases"]

    with httpx.Client(timeout=120) as c:
        health = c.get(f"{url}/health")          # first call also wakes a cold container
        info = c.get(f"{url}/pipeline-info")
        rows = []
        for case in cases:
            local = round(float(pipe.predict(pd.DataFrame([case["input"]])[RAW_COLUMNS])[0]), 3)
            r = c.post(f"{url}/predict", json=case["input"])
            deployed = r.json().get("predicted_rate_per_1000") if r.status_code == 200 else None
            ok = (r.status_code == 200 and abs(deployed - local) <= TOL
                  and abs(local - case["predicted_rate_per_1000"]) <= TOL)
            rows.append({"label": case["label"], "fixture": case["predicted_rate_per_1000"],
                         "local": local, "deployed": deployed, "status": r.status_code, "match": ok})
        invalid = c.post(f"{url}/predict", json={**cases[0]["input"], "reliable": -1})
        extra = c.post(f"{url}/predict", json={**cases[0]["input"], "unexpected": 1})
        unknown = c.get(f"{url}/npas/999999/outlook")

    checks = {
        "health_200": health.status_code == 200,
        "deployed_model_sha_matches_local": health.status_code == 200
            and health.json().get("model_sha256") == meta["artifact_sha256"][:12],
        "deployed_sklearn_matches_artifact": health.status_code == 200
            and health.json().get("scikit_learn") == meta["library_versions"]["scikit-learn"],
        "pipeline_info_200": info.status_code == 200,
        "all_predictions_match": all(r["match"] for r in rows),
        "negative_count_422": invalid.status_code == 422,
        "extra_field_422": extra.status_code == 422,
        "unknown_npa_404": unknown.status_code == 404,
    }
    report = {"api_url": url, "docs_url": f"{url}/docs",
              "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "local_model_sha256": meta["artifact_sha256"][:12],
              "deployed_health": health.json() if health.status_code == 200 else health.status_code,
              "tolerance": TOL, "predictions": rows, "checks": checks, "passed": all(checks.values())}
    (HERE / "verify_deployed.json").write_text(json.dumps(report, indent=2))

    for r in rows:
        print(f"{'MATCH' if r['match'] else 'DIFF ':5}  {r['label']:24} fixture={r['fixture']:<8} "
              f"local={r['local']:<8} deployed={r['deployed']}")
    for k, v in checks.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
    print("wrote api/verify_deployed.json |", "ALL PASSED" if report["passed"] else "FAILURES")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL))
