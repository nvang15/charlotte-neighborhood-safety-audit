# D4: fitted pipeline and API

Predicts a Charlotte NPA's **police-reported** reliably-reported crime rate (motor vehicle theft, burglary,
robbery per 1,000 residents) for the next year. It is the D3 selected model (M2 Poisson regression) rebuilt as a
scikit-learn `Pipeline` and served with FastAPI. It does not measure safety, and prediction is not causation.

```
CrimeFeatureBuilder (custom)  ->  StandardScaler  ->  PoissonRegressor
raw NPA-year facts (8 fields)     9 model features    rate per 1,000, weighted by residents/1000
```

`CrimeFeatureBuilder` (`safety_pipeline/transformers.py`) turns raw counts and NPA facts into the D3 features
(log counts, discretionary share, log population, log jobs per resident, log density, previous-year rate). It
rejects missing or impossible inputs and records the training range so the API can flag out-of-range requests.

## Live service

- API: https://jconrad8--charlotte-npa-crime-rate-api-serve.us-east.modal.run
- Interactive docs: https://jconrad8--charlotte-npa-crime-rate-api-serve.us-east.modal.run/docs
- Local vs deployed check: [`verify_deployed.json`](verify_deployed.json) (written by `verify_deployed.py`)

The first request after idle can take a few seconds while Modal starts a container.

## Rebuild and run (from the repo root)

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r api/requirements.txt -r d3_modeling/requirements.txt
.venv/bin/python api/train.py                      # fits on target years <= 2024, writes api/artifacts/
PYTHONPATH=api .venv/bin/python api/make_golden.py # fixed inputs/outputs used by tests and Postman
cd api && ../.venv/bin/python -m pytest -q         # 13 tests: 422, 503, 404, golden outputs
../.venv/bin/uvicorn app:app --port 8700           # then open http://localhost:8700/docs
```

`train.py` needs the D3 data in `d3_modeling/data/` (see `d3_modeling/run_all.sh` to refetch it). The 2025 target
year is never used for fitting or scored here; it is reserved for the D6 final test.

## Endpoints

| Method and path | Purpose | Errors |
|---|---|---|
| `GET /health` | model loaded? | 503 if artifact unavailable |
| `GET /pipeline-info` | steps, inputs, training window, versions, coefficients, limitations | 503 |
| `POST /predict` | predict from the 8 raw inputs | 422 invalid input, 503 |
| `GET /npas` | NPA ids available | 503 |
| `GET /npas/{npa}/outlook` | next-year outlook from an NPA's latest observed inputs | 404 unknown NPA, 503 |

The artifact is loaded once per server process. The service refuses to serve (503) if the artifact is missing
or was built with a different scikit-learn version than the installed one. Test 503 without touching production:
`ARTIFACT_DIR=/some/empty/dir uvicorn app:app`.

## Deploy (manual)

```bash
modal deploy api/modal_app.py     # needs `modal setup` once; prints the API URL; docs at <url>/docs
PYTHONPATH=api .venv/bin/python api/verify_deployed.py   # local vs deployed outputs -> api/verify_deployed.json
```

`verify_deployed.py` predicts every case in `tests/golden.json` with the local artifact and with the deployed
`POST /predict`, and checks that they match (to 3 decimals) along with the deployed model hash, scikit-learn
version, `/health`, `/pipeline-info`, 422 for invalid input, and 404 for an unknown NPA. 503 is tested locally only.

## Known limits

- NPA population and jobs are single snapshots (QOL profile), not year-specific; NPAs under 500 residents are excluded.
- Small-population NPAs give volatile rates; check the sample size before reading a rate.
- Inputs are reported incidents, which depend on reporting and policing, not just on crime.
