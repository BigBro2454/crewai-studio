"""LLM provider factory – returns a crewai.LLM instance for the chosen provider."""
from __future__ import annotations

import os
from typing import Any

from crewai import LLM

from backend.config.settings import Settings, get_settings


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> LLM:
    """Return a configured :class:`crewai.LLM` for *provider*.

    Args:
        provider: One of ``"openai"``, ``"anthropic"``, ``"google"``.
                  Defaults to ``settings.default_llm_provider``.
        model:    Override the model name from settings.
        **kwargs: Extra kwargs forwarded to :class:`crewai.LLM`.

    Raises:
        ValueError: When the provider is not supported or the API key is missing.
    """
    settings: Settings = get_settings()
    provider = provider or settings.default_llm_provider

    match provider:
        case "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is not set")
            return LLM(
                model=model or settings.openai_model,
                api_key=settings.openai_api_key,
                **kwargs,
            )
        case "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY is not set")
            return LLM(
                model=f"anthropic/{model or settings.anthropic_model}",
                api_key=settings.anthropic_api_key,
                **kwargs,
            )
        case "google":
            api_key = settings.google_api_key or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY is not set")
            selected_model = model or os.getenv("MODEL") or settings.gemini_model
            if not selected_model.startswith("gemini/"):
                selected_model = f"gemini/{selected_model}"
            return LLM(
                model=selected_model,
                api_key=api_key,
                **kwargs,
            )
        case _:
            raise ValueError(f"Unsupported LLM provider: {provider!r}")
