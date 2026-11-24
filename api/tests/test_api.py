import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app as app_module

ART = Path(__file__).resolve().parents[1] / "artifacts"
VALID = {"reliable": 180, "property_other": 520, "violent_other": 160, "discretionary": 90,
         "population": 9500, "jobs": 4200, "area_acres": 1300, "reliable_prev": 160}


@pytest.fixture(scope="module")
def client():
    with TestClient(app_module.app) as c:
        yield c


def test_health_and_info(client):
    assert client.get("/health").json()["status"] == "ok"
    info = client.get("/pipeline-info").json()
    assert info["steps"] == ["features", "scale", "glm"]
    assert info["custom_transformer"].endswith("CrimeFeatureBuilder")


def test_valid_predict(client):
    r = client.post("/predict", json=VALID)
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_rate_per_1000"] > 0
    assert 0 <= body["percentile_among_npas"] <= 100
    assert body["expected_count"] == pytest.approx(body["predicted_rate_per_1000"] * 9.5, rel=1e-2)


@pytest.mark.parametrize("bad", [
    {**VALID, "reliable": -1}, {**VALID, "population": 100}, {**VALID, "area_acres": 0},
    {**VALID, "jobs": "many"}, {**VALID, "surprise": 1}, {k: v for k, v in VALID.items() if k != "jobs"}, {}])
def test_invalid_returns_422(client, bad):
    assert client.post("/predict", json=bad).status_code == 422


def test_outlook_and_404(client):
    npa = client.get("/npas").json()["npas"][0]
    assert client.get(f"/npas/{npa}/outlook").status_code == 200
    assert client.get("/npas/99999/outlook").status_code == 404


def test_golden_outputs_match_saved_fixture(client):
    """Same inputs must give the same outputs locally and on the deployed service."""
    fx = json.loads((Path(__file__).parent / "golden.json").read_text())
    for case in fx["cases"]:
        got = client.post("/predict", json=case["input"]).json()
        assert got["predicted_rate_per_1000"] == pytest.approx(case["predicted_rate_per_1000"], abs=1e-3)


def test_missing_artifact_is_503(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))  # empty dir: nothing to load
    with TestClient(app_module.app) as c:
        for path in ("/health", "/pipeline-info", "/npas"):
            assert c.get(path).status_code == 503, path
        assert c.post("/predict", json=VALID).status_code == 503


def test_sklearn_version_mismatch_is_503(tmp_path, monkeypatch):
    for f in ART.iterdir():
        shutil.copy(f, tmp_path / f.name)
    meta = json.loads((tmp_path / "metadata.json").read_text())
    meta["library_versions"]["scikit-learn"] = "0.0.1"
    (tmp_path / "metadata.json").write_text(json.dumps(meta))
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    with TestClient(app_module.app) as c:
        r = c.post("/predict", json=VALID)
        assert r.status_code == 503 and "scikit-learn" in r.json()["detail"]
