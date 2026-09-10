"""API router – crew management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.crews import get_crew_configs, get_crew_class
from backend.models.schemas import CrewConfig

router = APIRouter(prefix="/crews", tags=["crews"])
templates = Jinja2Templates(directory="ui/templates")


@router.get("", response_model=list[CrewConfig])
async def list_crews() -> list[CrewConfig]:
    """Return all registered crew configurations."""
    return get_crew_configs()


@router.get("/{crew_name}", response_model=CrewConfig)
async def get_crew(crew_name: str) -> CrewConfig:
    """Return a single crew's configuration."""
    try:
        cls = get_crew_class(crew_name)
        return cls.config()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── HTMX partial ──────────────────────────────────────────────────────────────

@router.get("/{crew_name}/detail", response_class=HTMLResponse)
async def crew_detail_partial(request: Request, crew_name: str) -> HTMLResponse:
    """Return an HTMX partial for the crew detail panel."""
    try:
        cls = get_crew_class(crew_name)
        config = cls.config()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return templates.TemplateResponse(
        request=request,
        name="partials/crew_detail.html",
        context={"crew": config},
    )
