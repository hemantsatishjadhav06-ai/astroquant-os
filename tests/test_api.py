"""Smoke tests for the FastAPI Discovery Lab service (offline: synthetic source)."""
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from astroquant.api.app import app  # noqa: E402

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_dashboard_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "Discovery Lab" in r.text and "<svg" not in r.text[:50]  # it's the HTML page


def test_astro_endpoint():
    r = client.get("/astro/2024-01-01")
    assert r.status_code == 200
    planets = {p["body"]: p for p in r.json()["planets"]}
    assert planets["Jupiter"]["sign_name"] == "Aries"     # verified known position
    assert len(planets) == 9


def test_lab_run_endpoint():
    r = client.post("/lab/run", params={
        "symbols": "NIFTY", "source": "synthetic",
        "start": "2019-01-01", "end": "2022-12-31", "permutations": 6,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["total_tested"] == 6
    assert d["n_survivors"] == 0                          # synthetic noise => honest null
    assert len(d["leaderboard"]) == 6
    assert {"hypothesis_id", "verdict", "incremental_lift", "dsr"} <= set(d["leaderboard"][0])
