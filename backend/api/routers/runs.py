"""API router – crew run endpoints with SSE streaming."""
from __future__ import annotations

import asyncio
import html
import re
import sys
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from sse_starlette.sse import EventSourceResponse

from backend.crews import get_crew_class
from backend.models.schemas import RunRequest, RunResult, RunStatus
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
    """Background task: build and kickoff the crew, stream logs via buffer."""
    await run_store.update_status(run_id, RunStatus.RUNNING)
    _log_buffers[run_id] = [f"Initializing {crew_name.title()} crew..."]

    try:
        cls = get_crew_class(crew_name)
        crew = cls.build()

        def _run():
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = BufferTee(_log_buffers[run_id], old_stdout)
            sys.stderr = BufferTee(_log_buffers[run_id], old_stderr)
            try:
                return crew.kickoff(inputs=inputs)
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

        result = await asyncio.to_thread(_run)
        output = result.raw if hasattr(result, "raw") else str(result)
        await run_store.update_status(run_id, RunStatus.COMPLETED, output=output)
    except Exception as exc:
        err_msg = str(exc)
        if run_id in _log_buffers:
            _log_buffers[run_id].append(f"Error: {err_msg}")
        await run_store.update_status(run_id, RunStatus.FAILED, error=err_msg)
    finally:
        # Signal end of stream with sentinel
        if run_id in _log_buffers:
            _log_buffers[run_id].append("__DONE__")


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


@router.get("/{run_id}", response_model=RunResult)
async def get_run(run_id: UUID) -> RunResult:
    run = await run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


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
                    if run and run.status == RunStatus.COMPLETED:
                        output_html = md_parser.render(run.output or "")
                        yield {
                            "event": "status",
                            "data": '<span class="text-xs px-2.5 py-1 rounded-full bg-emerald-900/60 text-emerald-300 border border-emerald-700/50 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>Completed</span>',
                        }
                        yield {
                            "event": "done",
                            "data": f'<div class="mt-4 p-5 bg-gray-950 border border-emerald-800/40 rounded-xl"><div class="flex items-center gap-2 font-semibold text-emerald-400 mb-3 text-sm"><span>✅</span> Output Report</div><div class="prose prose-invert max-w-none text-gray-200 text-sm leading-relaxed">{output_html}</div></div>',
                        }
                    else:
                        err_text = html.escape(run.error or "Unknown error" if run else "Run failed")
                        yield {
                            "event": "status",
                            "data": '<span class="text-xs px-2.5 py-1 rounded-full bg-red-900/60 text-red-300 border border-red-700/50 flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-red-400"></span>Failed</span>',
                        }
                        yield {
                            "event": "done",
                            "data": f'<div class="mt-4 p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-red-300 text-xs"><div class="font-semibold text-sm text-red-400 mb-1">❌ Execution Error</div><pre class="font-mono whitespace-pre-wrap">{err_text}</pre></div>',
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
    return templates.TemplateResponse(
        request=request,
        name="partials/run_detail.html",
        context={"run": run},
    )
