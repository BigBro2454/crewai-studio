"""API router – crew run endpoints with SSE streaming, SQLite persistence, and export engine."""
from __future__ import annotations

import asyncio
import html
import re
import sys
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from sse_starlette.sse import EventSourceResponse

from backend.crews import get_crew_class
from backend.crews.mock_engine import MockCrewEngine
from backend.models.schemas import RunRequest, RunResult, RunStatus
from backend.utils.benchmark import BenchmarkEngine, BenchmarkSummary
from backend.utils.exporter import RunExporter
from backend.utils.guardrails import CrewGuardrails, GuardrailReport
from backend.utils.run_store import run_store

router = APIRouter(prefix="/runs", tags=["runs"])
templates = Jinja2Templates(directory="ui/templates")
md_parser = MarkdownIt()

# Regex to strip ANSI terminal escape codes
ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Simple in-process log buffer per run_id for SSE streaming
_log_buffers: dict[UUID, list[str]] = {}


class BufferTee:
    """Redirects writes to both original stream and the in-memory run buffer."""

    def __init__(self, buffer: list[str], original):
        self.buffer = buffer
        self.original = original

    def write(self, s: str):
        try:
            self.original.write(s)
            self.original.flush()
        except Exception:
            pass

        cleaned = ANSI_PATTERN.sub("", s).strip()
        if cleaned:
            self.buffer.append(cleaned)

    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass


async def _execute_crew(run_id: UUID, crew_name: str, inputs: dict) -> None:
    """Background task: evaluate guardrails, build and kickoff the crew or mock engine, stream logs, track telemetry and persist."""
    await run_store.update_status(run_id, RunStatus.RUNNING)
    _log_buffers[run_id] = [f"Initializing {crew_name.title()} crew..."]

    # 1. Evaluate input guardrails
    clean_inputs, in_guard = CrewGuardrails.evaluate_inputs(inputs)
    if in_guard.sanitized_items:
        _log_buffers[run_id].append(
            f"🛡️ [Guardrails] Sanitized PII in input: {', '.join(in_guard.sanitized_items)} ({in_guard.latency_ms}ms)"
        )

    if in_guard.blocked:
        err_msg = f"Security Policy Violation: Blocked adversarial input patterns [{', '.join(in_guard.violations)}]"
        _log_buffers[run_id].append(f"❌ [Guardrails] {err_msg}")
        await run_store.update_status(
            run_id,
            RunStatus.FAILED,
            error=err_msg,
            telemetry={"metadata": {"guardrails": in_guard.model_dump()}},
        )
        if run_id in _log_buffers:
            _log_buffers[run_id].append("__DONE__")
            await run_store.save_logs(run_id, _log_buffers[run_id])
        return

    # Check for mock execution mode
    is_mock = clean_inputs.get("mock") is True or os.getenv("MOCK_CREW", "").lower() in ("true", "1")

    try:
        if is_mock:
            _log_buffers[run_id].append("⚡ [Runtime] Executing in deterministic Mock Mode (Offline Zero-Token)...")
            output = await MockCrewEngine.execute_mock(crew_name, clean_inputs, _log_buffers[run_id], step_delay=0.03)
        else:
            cls = get_crew_class(crew_name)
            crew = cls.build()

            def _run():
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = BufferTee(_log_buffers[run_id], old_stdout)
                sys.stderr = BufferTee(_log_buffers[run_id], old_stderr)
                try:
                    return crew.kickoff(inputs=clean_inputs)
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr

            result = await asyncio.to_thread(_run)
            output = result.raw if hasattr(result, "raw") else str(result)

        # 2. Evaluate output guardrails
        clean_output, out_guard = CrewGuardrails.evaluate_output(output)
        if out_guard.sanitized_items:
            _log_buffers[run_id].append(
                f"🛡️ [Guardrails] Sanitized PII in output: {', '.join(out_guard.sanitized_items)}"
            )

        telemetry_meta = {
            "metadata": {
                "guardrails": {
                    "input": in_guard.model_dump(),
                    "output": out_guard.model_dump(),
                    "blocked": False,
                    "sanitized_items": in_guard.sanitized_items + out_guard.sanitized_items,
                },
                "is_mock": is_mock,
            }
        }
        await run_store.update_status(run_id, RunStatus.COMPLETED, output=clean_output, telemetry=telemetry_meta)
    except Exception as exc:
        err_msg = str(exc)
        if run_id in _log_buffers:
            _log_buffers[run_id].append(f"Error: {err_msg}")
        await run_store.update_status(
            run_id,
            RunStatus.FAILED,
            error=err_msg,
            telemetry={"metadata": {"guardrails": in_guard.model_dump(), "is_mock": is_mock}},
        )
    finally:
        # Signal end of stream with sentinel
        if run_id in _log_buffers:
            _log_buffers[run_id].append("__DONE__")
            await run_store.save_logs(run_id, _log_buffers[run_id])


# ── Run creation endpoint (handles Form and JSON) ─────────────────────────────

@router.post("", status_code=202)
async def create_run(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Kick off a crew run asynchronously. Supports both HTMX Form and JSON payloads."""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body = await request.json()
        crew_name = body.get("crew_name")
        inputs = body.get("inputs")
        if inputs is None:
            inputs = {k: v for k, v in body.items() if k != "crew_name"}
    else:
        form = await request.form()
        crew_name = form.get("crew_name")
        inputs = {k: v for k, v in form.items() if k != "crew_name"}

    if not crew_name:
        raise HTTPException(status_code=422, detail="Missing crew_name field")

    run = RunResult(crew_name=str(crew_name), inputs=inputs)
    await run_store.create(run)
    background_tasks.add_task(_execute_crew, run.run_id, str(crew_name), inputs)

    # If requested by HTMX, return the active run component directly
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="partials/active_run.html",
            context={"run": run},
        )

    return JSONResponse(run.model_dump(mode="json"), status_code=202)


@router.get("", response_model=list[RunResult])
async def list_runs() -> list[RunResult]:
    return await run_store.list_all()


# ── Benchmark & Token Economics Endpoints ────────────────────────────────────

@router.get("/benchmark/summary", response_model=BenchmarkSummary)
async def get_benchmark_summary() -> BenchmarkSummary:
    """Compute aggregate benchmark metrics and multi-model token economics across all runs."""
    runs = await run_store.list_all()
    return BenchmarkEngine.analyze_runs(runs)


@router.get("/benchmark/export")
async def export_benchmark_markdown() -> Response:
    """Download executive Markdown scorecard for cross-run benchmarks."""
    runs = await run_store.list_all()
    summary = BenchmarkEngine.analyze_runs(runs)
    md_content = BenchmarkEngine.to_markdown(summary)
    headers = {
        "Content-Disposition": 'attachment; filename="crewai_studio_benchmark_scorecard.md"'
    }
    return Response(content=md_content, media_type="text/markdown", headers=headers)


@router.get("/{run_id}", response_model=RunResult)
async def get_run(run_id: UUID) -> RunResult:
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.get("/{run_id}/logs")
async def get_run_logs(run_id: UUID) -> list[str]:
    """Return persisted execution logs for a run."""
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    # Check active memory buffer first, then persisted SQLite logs
    if run_id in _log_buffers:
        return [line for line in _log_buffers[run_id] if line != "__DONE__"]
    return await run_store.get_logs(run_id)


# ── Export endpoints ─────────────────────────────────────────────────────────

@router.get("/{run_id}/export/json")
async def export_run_json(run_id: UUID) -> Response:
    """Download full run result, telemetry, and logs as structured JSON."""
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    logs = (
        _log_buffers.get(run_id)
        if run_id in _log_buffers
        else await run_store.get_logs(run_id)
    )
    json_content = RunExporter.to_json(run, logs)
    headers = {
        "Content-Disposition": f'attachment; filename="crew_run_{run_id}.json"'
    }
    return Response(content=json_content, media_type="application/json", headers=headers)


@router.get("/{run_id}/export/markdown")
@router.get("/{run_id}/export/md")
async def export_run_markdown(run_id: UUID) -> Response:
    """Download comprehensive Google L5 execution report as Markdown."""
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    logs = (
        _log_buffers.get(run_id)
        if run_id in _log_buffers
        else await run_store.get_logs(run_id)
    )
    md_content = RunExporter.to_markdown(run, logs)
    headers = {
        "Content-Disposition": f'attachment; filename="crew_run_{run_id}.md"'
    }
    return Response(
        content=md_content,
        media_type="text/markdown; charset=utf-8",
        headers=headers,
    )


# ── SSE log stream ─────────────────────────────────────────────────────────────

@router.get("/{run_id}/stream")
async def stream_run_logs(run_id: UUID) -> EventSourceResponse:
    """Server-Sent Events stream of run log lines and completion events."""

    async def generator():
        sent = 0
        while True:
            buf = _log_buffers.get(run_id, [])
            while sent < len(buf):
                line = buf[sent]
                sent += 1
                if line == "__DONE__":
                    run = await run_store.get(run_id)
                    duration_str = (
                        f"{run.telemetry.duration_seconds:.2f}s"
                        if run and run.telemetry.duration_seconds is not None
                        else "N/A"
                    )
                    export_buttons = (
                        f'<div class="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between text-xs">'
                        f'<span class="text-gray-400 font-mono">⚡ Duration: <span class="text-white font-semibold">{duration_str}</span> | Logs: <span class="text-white font-semibold">{run.telemetry.log_line_count if run else 0}</span></span>'
                        f'<div class="flex items-center gap-2">'
                        f'<a href="/api/runs/{run_id}/export/markdown" download class="px-2.5 py-1 bg-gray-900 hover:bg-gray-800 text-gray-200 rounded border border-gray-700 flex items-center gap-1 transition">📥 Markdown</a>'
                        f'<a href="/api/runs/{run_id}/export/json" download class="px-2.5 py-1 bg-gray-900 hover:bg-gray-800 text-gray-200 rounded border border-gray-700 flex items-center gap-1 transition">📥 JSON</a>'
                        f'</div></div>'
                    )

                    if run and run.status == RunStatus.COMPLETED:
                        output_html = md_parser.render(run.output or "")
                        yield {
                            "event": "status",
                            "data": f'<span class="text-xs px-2.5 py-1 rounded-full bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Completed ({duration_str})</span>',
                        }
                        yield {
                            "event": "done",
                            "data": (
                                f'<div class="mt-4 p-5 bg-gray-950 border border-emerald-800/40 rounded-xl">'
                                f'<div class="flex items-center gap-2 font-semibold text-emerald-400 mb-3 text-sm"><span>✅</span> Output Report</div>'
                                f'<div class="prose prose-invert max-w-none text-gray-200 text-sm leading-relaxed">{output_html}</div>'
                                f'{export_buttons}'
                                f'</div>'
                            ),
                        }
                    else:
                        err_text = html.escape(run.error or "Unknown error" if run else "Run failed")
                        yield {
                            "event": "status",
                            "data": f'<span class="text-xs px-2.5 py-1 rounded-full bg-red-900/60 text-red-300 border border-red-700/50 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Failed ({duration_str})</span>',
                        }
                        yield {
                            "event": "done",
                            "data": (
                                f'<div class="mt-4 p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-xs">'
                                f'<div class="font-semibold text-sm text-red-400 mb-1">❌ Execution Error</div>'
                                f'<pre class="font-mono whitespace-pre-wrap">{err_text}</pre>'
                                f'{export_buttons}'
                                f'</div>'
                            ),
                        }
                    return

                escaped = html.escape(line)
                yield {
                    "event": "log",
                    "data": f'<div class="leading-relaxed text-gray-300 font-mono text-xs select-text">{escaped}</div>',
                }

            await asyncio.sleep(0.3)

    return EventSourceResponse(generator())


# ── HTMX partials ─────────────────────────────────────────────────────────────

@router.get("/ui/list", response_class=HTMLResponse)
async def runs_list_partial(request: Request) -> HTMLResponse:
    runs = await run_store.list_all()
    return templates.TemplateResponse(
        request=request,
        name="partials/runs_list.html",
        context={"runs": runs},
    )


@router.get("/{run_id}/ui", response_class=HTMLResponse)
async def run_detail_partial(request: Request, run_id: UUID) -> HTMLResponse:
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    logs = await run_store.get_logs(run_id)
    return templates.TemplateResponse(
        request=request,
        name="partials/run_detail.html",
        context={"run": run, "logs": logs},
    )
