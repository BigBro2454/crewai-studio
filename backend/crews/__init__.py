"""Registry of all available crew definitions."""
from __future__ import annotations

from backend.models.schemas import CrewConfig

# Import individual crew factories
from backend.crews.research_crew import ResearchCrew
from backend.crews.content_crew import ContentCrew


CREW_REGISTRY: dict[str, type] = {
    "research": ResearchCrew,
    "content": ContentCrew,
}


def get_crew_configs() -> list[CrewConfig]:
    """Return metadata configs for all registered crews."""
    return [crew_cls.config() for crew_cls in CREW_REGISTRY.values()]


def get_crew_class(name: str):
    """Lookup crew class by name."""
    cls = CREW_REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"No crew named {name!r}. Available: {list(CREW_REGISTRY)}")
    return cls
