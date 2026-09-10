"""FastAPI application factory."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.api.routers import crews, runs
from backend.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Static files ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="ui/static"), name="static")

# ── Templates ─────────────────────────────────────────────────────────────────
templates = Jinja2Templates(directory="ui/templates")

# Add enumerate as a global so templates can use it
templates.env.globals["enumerate"] = enumerate


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(crews.router, prefix="/api")
app.include_router(runs.router, prefix="/api")


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Dashboard / home page."""
    from backend.crews import get_crew_configs
    configs = get_crew_configs()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"crews": configs, "app_name": settings.app_name},
    )


@app.get("/crews/{crew_name}", response_class=HTMLResponse)
async def crew_page(request: Request, crew_name: str) -> HTMLResponse:
    """Individual crew page with run form."""
    from backend.crews import get_crew_class
    cls = get_crew_class(crew_name)
    config = cls.config()
    return templates.TemplateResponse(
        request=request,
        name="crews/detail.html",
        context={"crew": config, "app_name": settings.app_name},
    )


@app.get("/runs", response_class=HTMLResponse)
async def runs_page(request: Request) -> HTMLResponse:
    """Runs history page."""
    from backend.utils.run_store import run_store
    runs_list = await run_store.list_all()
    return templates.TemplateResponse(
        request=request,
        name="crews/runs.html",
        context={"runs": runs_list, "app_name": settings.app_name},
    )
