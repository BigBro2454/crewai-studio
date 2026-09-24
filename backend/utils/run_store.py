"""Thread-safe SQLite and in-memory persistence store for crew run results and telemetry."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from backend.models.schemas import RunResult, RunStatus, RunTelemetry


class RunStore:
    """Thread-safe, dual-layer (SQLite + in-memory cache) store for crew run results."""

    def __init__(
        self,
        db_path: Path | str = "data/runs.db",
        max_cache_size: int = 200,
    ) -> None:
        self.db_path = str(db_path)
        self.max_cache_size = max_cache_size
        self._cache: OrderedDict[UUID, RunResult] = OrderedDict()
        self._lock = asyncio.Lock()
        self._init_db()
        self._warm_cache()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path != ":memory:":
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    crew_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    inputs TEXT,
                    output TEXT,
                    error TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_seconds REAL,
                    log_line_count INTEGER DEFAULT 0,
                    telemetry TEXT,
                    logs TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)"
            )
            conn.commit()

    def _warm_cache(self) -> None:
        """Load recent runs from SQLite into in-memory cache."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                    (self.max_cache_size,),
                )
                rows = cursor.fetchall()
                for row in reversed(rows):
                    run = self._row_to_run(row)
                    self._cache[run.run_id] = run
        except Exception:
            pass

    def _row_to_run(self, row: sqlite3.Row) -> RunResult:
        inputs = json.loads(row["inputs"]) if row["inputs"] else {}
        telemetry_data = json.loads(row["telemetry"]) if row["telemetry"] else {}
        
        telemetry = RunTelemetry(
            duration_seconds=row["duration_seconds"],
            log_line_count=row["log_line_count"] or 0,
            output_length=len(row["output"] or ""),
            input_keys=list(inputs.keys()),
            has_error=bool(row["error"]),
            metadata=telemetry_data.get("metadata", {}),
        )

        started_at = (
            datetime.fromisoformat(row["started_at"]) if row["started_at"] else None
        )
        finished_at = (
            datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None
        )

        return RunResult(
            run_id=UUID(row["run_id"]),
            crew_name=row["crew_name"],
            status=RunStatus(row["status"]),
            inputs=inputs,
            output=row["output"],
            error=row["error"],
            started_at=started_at,
            finished_at=finished_at,
            telemetry=telemetry,
        )

    async def create(self, run: RunResult) -> RunResult:
        now_iso = datetime.now(timezone.utc).isoformat()
        telemetry_dict = run.telemetry.model_dump()
        inputs_json = json.dumps(run.inputs)
        telemetry_json = json.dumps(telemetry_dict)

        async with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO runs (
                        run_id, crew_name, status, inputs, output, error,
                        started_at, finished_at, duration_seconds, log_line_count,
                        telemetry, logs, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(run.run_id),
                        run.crew_name,
                        run.status.value,
                        inputs_json,
                        run.output,
                        run.error,
                        run.started_at.isoformat() if run.started_at else None,
                        run.finished_at.isoformat() if run.finished_at else None,
                        run.telemetry.duration_seconds,
                        run.telemetry.log_line_count,
                        telemetry_json,
                        json.dumps([]),
                        now_iso,
                    ),
                )
                conn.commit()

            if len(self._cache) >= self.max_cache_size:
                self._cache.popitem(last=False)
            self._cache[run.run_id] = run

        return run

    async def get(self, run_id: UUID) -> RunResult | None:
        async with self._lock:
            if run_id in self._cache:
                return self._cache[run_id]

            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM runs WHERE run_id = ?", (str(run_id),)
                )
                row = cursor.fetchone()
                if row:
                    run = self._row_to_run(row)
                    self._cache[run.run_id] = run
                    return run
        return None

    async def save_logs(self, run_id: UUID, logs: list[str]) -> None:
        cleaned_logs = [line for line in logs if line != "__DONE__"]
        async with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE runs SET logs = ?, log_line_count = ? WHERE run_id = ?",
                    (json.dumps(cleaned_logs), len(cleaned_logs), str(run_id)),
                )
                conn.commit()

            if run_id in self._cache:
                self._cache[run_id].telemetry.log_line_count = len(cleaned_logs)

    async def get_logs(self, run_id: UUID) -> list[str]:
        async with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT logs FROM runs WHERE run_id = ?", (str(run_id),)
                )
                row = cursor.fetchone()
                if row and row["logs"]:
                    try:
                        return json.loads(row["logs"])
                    except Exception:
                        return []
        return []

    async def update_status(
        self,
        run_id: UUID,
        status: RunStatus,
        output: str | None = None,
        error: str | None = None,
        telemetry: RunTelemetry | dict[str, Any] | None = None,
    ) -> RunResult | None:
        async with self._lock:
            run = self._cache.get(run_id)
            if run is None:
                # check DB
                with self._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT * FROM runs WHERE run_id = ?", (str(run_id),)
                    )
                    row = cursor.fetchone()
                    if row:
                        run = self._row_to_run(row)
                        self._cache[run.run_id] = run

            if run is None:
                return None

            run.status = status
            if output is not None:
                run.output = output
                run.telemetry.output_length = len(output)
            if error is not None:
                run.error = error
                run.telemetry.has_error = True

            now = datetime.now(timezone.utc)
            if status == RunStatus.RUNNING:
                run.started_at = now
            elif status in (RunStatus.COMPLETED, RunStatus.FAILED):
                run.finished_at = now
                if run.started_at:
                    delta = (run.finished_at - run.started_at).total_seconds()
                    run.telemetry.duration_seconds = round(delta, 3)

            if telemetry is not None:
                if isinstance(telemetry, RunTelemetry):
                    run.telemetry = telemetry
                elif isinstance(telemetry, dict):
                    for k, v in telemetry.items():
                        if hasattr(run.telemetry, k):
                            setattr(run.telemetry, k, v)

            # Persist update to SQLite
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE runs SET
                        status = ?,
                        output = ?,
                        error = ?,
                        started_at = ?,
                        finished_at = ?,
                        duration_seconds = ?,
                        log_line_count = ?,
                        telemetry = ?
                    WHERE run_id = ?
                    """,
                    (
                        run.status.value,
                        run.output,
                        run.error,
                        run.started_at.isoformat() if run.started_at else None,
                        run.finished_at.isoformat() if run.finished_at else None,
                        run.telemetry.duration_seconds,
                        run.telemetry.log_line_count,
                        json.dumps(run.telemetry.model_dump()),
                        str(run.run_id),
                    ),
                )
                conn.commit()

            return run

    async def list_all(self, limit: int = 100) -> list[RunResult]:
        async with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
                rows = cursor.fetchall()
                results = [self._row_to_run(row) for row in rows]
                for r in results:
                    self._cache[r.run_id] = r
                return results

    async def delete(self, run_id: UUID) -> bool:
        async with self._lock:
            self._cache.pop(run_id, None)
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM runs WHERE run_id = ?", (str(run_id),)
                )
                conn.commit()
                return cursor.rowcount > 0

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
            with self._get_connection() as conn:
                conn.execute("DELETE FROM runs")
                conn.commit()


# Singleton instance shared across the application
run_store = RunStore()
