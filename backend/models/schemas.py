"""Shared Pydantic models (request / response schemas)."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Agent schemas ─────────────────────────────────────────────────────────────

class AgentConfig(BaseModel):
    name: str
    role: str
    goal: str
    backstory: str
    llm_provider: LLMProvider = LLMProvider.OPENAI
    llm_model: str | None = None
    allow_delegation: bool = False
    verbose: bool = True


# ── Task schemas ──────────────────────────────────────────────────────────────

class TaskConfig(BaseModel):
    name: str
    description: str
    expected_output: str
    agent_name: str  # references AgentConfig.name


# ── Crew schemas ──────────────────────────────────────────────────────────────

class CrewConfig(BaseModel):
    name: str
    description: str
    agents: list[AgentConfig]
    tasks: list[TaskConfig]
    process: str = "sequential"  # sequential | hierarchical
    verbose: bool = True


# ── Run schemas ───────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    crew_name: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    crew_name: str
    status: RunStatus = RunStatus.PENDING
    inputs: dict[str, Any] = Field(default_factory=dict)
    output: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
