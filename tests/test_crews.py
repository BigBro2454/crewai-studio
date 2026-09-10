"""Tests for crew configurations and API endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.crews import get_crew_configs
from backend.models.schemas import RunRequest

client = TestClient(app)


def test_list_crews():
    configs = get_crew_configs()
    assert len(configs) >= 2
    names = [c.name for c in configs]
    assert "research" in names
    assert "content" in names


def test_api_list_crews():
    resp = client.get("/api/crews")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(c["name"] == "research" for c in data)


def test_api_get_crew():
    resp = client.get("/api/crews/research")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "research"
    assert len(data["agents"]) == 3
    assert len(data["tasks"]) == 3


def test_api_get_crew_not_found():
    resp = client.get("/api/crews/nonexistent")
    assert resp.status_code == 404


def test_api_create_run_bad_crew():
    resp = client.post(
        "/api/runs",
        json={"crew_name": "nonexistent", "inputs": {}},
    )
    # The run is created (202) but will fail asynchronously
    assert resp.status_code in (202, 422)


def test_api_list_runs():
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_dashboard_page():
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"CrewAI Studio" in resp.content


def test_crew_detail_page():
    resp = client.get("/crews/research")
    assert resp.status_code == 200
    assert b"Research" in resp.content
