"""Tests for SQLite persistence, run telemetry tracking, and Markdown/JSON export engine."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api.app import app
from backend.models.schemas import RunResult, RunStatus, RunTelemetry
from backend.utils.exporter import RunExporter
from backend.utils.run_store import RunStore, run_store

client = TestClient(app)


@pytest.fixture
def temp_store(tmp_path: Path) -> RunStore:
    """Create an isolated RunStore backed by a temporary SQLite file."""
    db_file = tmp_path / "test_runs.db"
    return RunStore(db_path=db_file)


@pytest.mark.asyncio
async def test_sqlite_run_store_lifecycle(temp_store: RunStore):
    # 1. Create run
    run_id = uuid4()
    run = RunResult(
        run_id=run_id,
        crew_name="research",
        inputs={"topic": "Quantum Computing"},
    )
    created = await temp_store.create(run)
    assert created.run_id == run_id
    assert created.status == RunStatus.PENDING

    # 2. Update to RUNNING
    updated_running = await temp_store.update_status(run_id, RunStatus.RUNNING)
    assert updated_running is not None
    assert updated_running.status == RunStatus.RUNNING
    assert updated_running.started_at is not None

    # 3. Save logs
    logs = [
        "Initializing Research crew...",
        "Task 1: Searching for Quantum Computing papers",
        "Task 2: Synthesizing results",
    ]
    await temp_store.save_logs(run_id, logs)
    stored_logs = await temp_store.get_logs(run_id)
    assert stored_logs == logs

    # 4. Complete run
    output_text = "# Executive Summary\nQuantum computing promises exponential speedup."
    completed = await temp_store.update_status(
        run_id,
        RunStatus.COMPLETED,
        output=output_text,
    )
    assert completed is not None
    assert completed.status == RunStatus.COMPLETED
    assert completed.finished_at is not None
    assert completed.telemetry.duration_seconds is not None
    assert completed.telemetry.duration_seconds >= 0.0
    assert completed.telemetry.log_line_count == 3
    assert completed.telemetry.output_length == len(output_text)
    assert completed.telemetry.has_error is False

    # 5. Verify persistence across new store instance pointing to same file
    new_store = RunStore(db_path=temp_store.db_path)
    loaded_run = await new_store.get(run_id)
    assert loaded_run is not None
    assert loaded_run.run_id == run_id
    assert loaded_run.crew_name == "research"
    assert loaded_run.status == RunStatus.COMPLETED
    assert loaded_run.output == output_text
    assert loaded_run.telemetry.duration_seconds == completed.telemetry.duration_seconds

    loaded_logs = await new_store.get_logs(run_id)
    assert loaded_logs == logs


@pytest.mark.asyncio
async def test_exporter_engine():
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    run = RunResult(
        run_id=run_id,
        crew_name="content",
        status=RunStatus.COMPLETED,
        inputs={"brand": "TechCorp", "tone": "Professional"},
        output="## Strategic Brief\nElevate developer trust through open-source tooling.",
        started_at=now,
        finished_at=now,
        telemetry=RunTelemetry(
            duration_seconds=3.45,
            log_line_count=4,
            output_length=62,
            has_error=False,
        ),
    )
    logs = ["Step 1: Drafting headline", "Step 2: Refining tone", "__DONE__"]

    # 1. JSON Export
    json_str = RunExporter.to_json(run, logs)
    assert json_str is not None
    parsed = json.loads(json_str)
    assert parsed["run_id"] == str(run_id)
    assert parsed["crew_name"] == "content"
    assert parsed["telemetry"]["duration_seconds"] == 3.45
    assert len(parsed["logs"]) == 2  # __DONE__ stripped

    # 2. Markdown Export
    md_str = RunExporter.to_markdown(run, logs)
    assert md_str is not None
    assert "# CrewAI Studio Execution Report: Content Crew" in md_str
    assert "✅ COMPLETED" in md_str
    assert "3.45s" in md_str
    assert "TechCorp" in md_str
    assert "Strategic Brief" in md_str
    assert "Step 1: Drafting headline" in md_str


def test_api_export_endpoints():
    # Insert test run directly into the global singleton store
    run_id = uuid4()
    run = RunResult(
        run_id=run_id,
        crew_name="research",
        status=RunStatus.COMPLETED,
        inputs={"query": "Autonomous Agents"},
        output="Autonomous agents leverage perception, action, and memory.",
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        telemetry=RunTelemetry(duration_seconds=1.2, log_line_count=2, output_length=57),
    )

    import asyncio
    asyncio.run(run_store.create(run))
    asyncio.run(run_store.save_logs(run_id, ["Agent 1 initialized", "Querying"]))

    # Test JSON export
    resp_json = client.get(f"/api/runs/{run_id}/export/json")
    assert resp_json.status_code == 200
    assert "application/json" in resp_json.headers["content-type"]
    assert f'filename="crew_run_{run_id}.json"' in resp_json.headers["content-disposition"]
    data = resp_json.json()
    assert data["crew_name"] == "research"

    # Test Markdown export
    resp_md = client.get(f"/api/runs/{run_id}/export/markdown")
    assert resp_md.status_code == 200
    assert "text/markdown" in resp_md.headers["content-type"]
    assert f'filename="crew_run_{run_id}.md"' in resp_md.headers["content-disposition"]
    assert "CrewAI Studio Execution Report" in resp_md.text

    # Test alias /export/md
    resp_alias = client.get(f"/api/runs/{run_id}/export/md")
    assert resp_alias.status_code == 200

    # Test Logs API
    resp_logs = client.get(f"/api/runs/{run_id}/logs")
    assert resp_logs.status_code == 200
    logs_data = resp_logs.json()
    assert isinstance(logs_data, list)
    assert len(logs_data) >= 2

    # Test Detail HTML Partial
    resp_ui = client.get(f"/api/runs/{run_id}/ui")
    assert resp_ui.status_code == 200
    assert "Research Crew Run" in resp_ui.text


def test_api_export_not_found():
    random_id = uuid4()
    resp = client.get(f"/api/runs/{random_id}/export/json")
    assert resp.status_code == 404

    resp_md = client.get(f"/api/runs/{random_id}/export/markdown")
    assert resp_md.status_code == 404

    resp_logs = client.get(f"/api/runs/{random_id}/logs")
    assert resp_logs.status_code == 404
