"""In-memory run store (replace with a DB adapter for persistence)."""
from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from uuid import UUID

from backend.models.schemas import RunResult, RunStatus


class RunStore:
    """Thread-safe, ordered, in-memory store for crew run results."""

    def __init__(self, max_size: int = 200) -> None:
        self._store: OrderedDict[UUID, RunResult] = OrderedDict()
        self._lock = asyncio.Lock()
        self.max_size = max_size

    async def create(self, run: RunResult) -> RunResult:
        async with self._lock:
            if len(self._store) >= self.max_size:
                self._store.popitem(last=False)  # evict oldest
            self._store[run.run_id] = run
        return run

    async def get(self, run_id: UUID) -> RunResult | None:
        return self._store.get(run_id)

    async def update_status(
        self,
        run_id: UUID,
        status: RunStatus,
        output: str | None = None,
        error: str | None = None,
    ) -> RunResult | None:
        async with self._lock:
            run = self._store.get(run_id)
            if run is None:
                return None
            run.status = status
            if output is not None:
                run.output = output
            if error is not None:
                run.error = error
            if status == RunStatus.RUNNING:
                run.started_at = datetime.now(timezone.utc)
            elif status in (RunStatus.COMPLETED, RunStatus.FAILED):
                run.finished_at = datetime.now(timezone.utc)
            return run

    async def list_all(self) -> list[RunResult]:
        return list(reversed(self._store.values()))


# Singleton instance shared across the application
run_store = RunStore()
