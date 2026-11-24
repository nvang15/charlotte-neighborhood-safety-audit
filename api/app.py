"""FastAPI service for the NPA reported-crime-rate pipeline (D4).

The fitted Pipeline is loaded once per server process (lifespan) and never retrained while
serving. If the artifact is missing, unreadable, or was built with a different scikit-learn
version than the one installed, the service stays up but model endpoints return 503.
"""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from safety_pipeline import RAW_COLUMNS

DEFAULT_ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


def load_bundle(art_dir: Path) -> dict:
    """Load pipeline + metadata + lookup tables. Raises RuntimeError with a plain reason."""
    try:
        meta = json.loads((art_dir / "metadata.json").read_text())
        want = meta["library_versions"]["scikit-learn"]
        if want != sklearn.__version__:
            raise RuntimeError(f"artifact built with scikit-learn {want}, server has {sklearn.__version__}")
        return {
            "pipeline": joblib.load(art_dir / "pipeline.joblib"),
            "meta": meta,
            "latest": pd.read_csv(art_dir / "npa_latest.csv").set_index("npa"),
            "reference": np.load(art_dir / "reference_predictions.npy"),
        }
    except RuntimeError:
        raise
    except Exception as e:  # missing file, corrupt pickle, bad JSON
        raise RuntimeError(f"{type(e).__name__}: {e}") from e


@asynccontextmanager
async def lifespan(app: FastAPI):
    art = Path(os.environ.get("ARTIFACT_DIR", DEFAULT_ARTIFACTS))
    app.state.bundle, app.state.error = None, None
    try:
        app.state.bundle = load_bundle(art)  # once per process
    except RuntimeError as e:
        app.state.error = str(e)
    yield


app = FastAPI(
    title="Charlotte NPA reported-crime-rate API",
    version="1.0.0",
    description=("Predicts next year's *police-reported* reliably-reported crime rate (motor vehicle theft, "
                 "burglary, robbery) per 1,000 residents for a Charlotte NPA. It does not measure safety, "
                 "and prediction does not establish causation."),
    lifespan=lifespan,
)


def bundle(request: Request) -> dict:
    b = request.app.state.bundle
    if b is None:
        raise HTTPException(503, detail=f"Model artifact unavailable: {request.app.state.error}")
    return b


class PredictRequest(BaseModel):
    """One NPA in one year t. Every field describes year t or earlier."""
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {
        "reliable": 180, "property_other": 520, "violent_other": 160, "discretionary": 90,
        "population": 9500, "jobs": 4200, "area_acres": 1300, "reliable_prev": 160}})
    reliable: int = Field(ge=0, le=100_000, description="Year-t motor vehicle theft + burglary + robbery reports")
    property_other: int = Field(ge=0, le=100_000, description="Year-t other property offense reports")
    violent_other: int = Field(ge=0, le=100_000, description="Year-t other violent offense reports")
    discretionary: int = Field(ge=0, le=100_000, description="Year-t police-activity-driven offense reports")
    population: float = Field(ge=500, le=1_000_000, description="Residents (NPAs under 500 are excluded)")
    jobs: float = Field(ge=0, le=2_000_000, description="Jobs located in the NPA")
    area_acres: float = Field(gt=0, le=1_000_000, description="NPA land area in acres")
    reliable_prev: int = Field(ge=0, le=100_000, description="Year t-1 reliable count (same definition as `reliable`)")


class Prediction(BaseModel):
    predicted_rate_per_1000: float
    expected_count: float
    percentile_among_npas: float = Field(description="Share (0-100) of NPAs whose latest-year prediction is below this one")
    out_of_range_features: list[str] = Field(description="Features outside the training range (treat the result with caution)")
    model_sha256: str


def predict_rows(b: dict, df: pd.DataFrame) -> list[Prediction]:
    pipe = b["pipeline"]
    rate = pipe.predict(df[RAW_COLUMNS])
    out = []
    for i, r in enumerate(rate):
        pct = float(np.searchsorted(b["reference"], r, side="left") / len(b["reference"]) * 100)
        oor = pipe.named_steps["features"].out_of_range(df[RAW_COLUMNS].iloc[[i]])
        out.append(Prediction(predicted_rate_per_1000=round(float(r), 3),
                              expected_count=round(float(r * df.population.iloc[i] / 1000), 2),
                              percentile_among_npas=round(pct, 1), out_of_range_features=oor,
                              model_sha256=b["meta"]["artifact_sha256"][:12]))
    return out


@app.get("/health", tags=["service"])
def health(request: Request):
    """Readiness: 200 when the model is loaded, 503 otherwise."""
    b = bundle(request)
    return {"status": "ok", "model_loaded": True, "scikit_learn": sklearn.__version__,
            "model_sha256": b["meta"]["artifact_sha256"][:12]}


@app.get("/pipeline-info", tags=["service"])
def pipeline_info(request: Request):
    """Steps, inputs, training window, library versions, coefficients, and limitations."""
    return bundle(request)["meta"]


@app.post("/predict", response_model=Prediction, tags=["model"])
def predict(req: PredictRequest, request: Request):
    b = bundle(request)
    return predict_rows(b, pd.DataFrame([req.model_dump()]))[0]


@app.get("/npas", tags=["data"])
def list_npas(request: Request):
    """NPA ids with their latest-year inputs (what the frontend uses to pick areas)."""
    b = bundle(request)
    return {"feature_year": int(b["latest"].feature_year.iloc[0]), "npas": sorted(int(i) for i in b["latest"].index)}


@app.get("/npas/{npa}/outlook", response_model=Prediction, tags=["data"])
def npa_outlook(npa: int, request: Request):
    """Next-year outlook for an NPA from its latest observed inputs."""
    b = bundle(request)
    if npa not in b["latest"].index:
        raise HTTPException(404, detail=f"Unknown NPA {npa}")
    return predict_rows(b, b["latest"].loc[[npa], RAW_COLUMNS])[0]
