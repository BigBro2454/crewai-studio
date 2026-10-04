"""Multi-stage security guardrails and PII masking for Crew inputs and outputs."""
from __future__ import annotations

import re
import time
from typing import Any
from pydantic import BaseModel, Field


# ── Guardrail Patterns ────────────────────────────────────────────────────────

INJECTION_PATTERNS = [
    (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?", re.IGNORECASE), "PROMPT_INJECTION_IGNORE_INSTRUCTIONS"),
    (re.compile(r"system\s+(?:prompt|override|directive)\s+bypass", re.IGNORECASE), "SYSTEM_PROMPT_OVERRIDE"),
    (re.compile(r"(?:you\s+are\s+now|act\s+as)\s+(?:DAN|jailbreak|unfiltered\s+AI)", re.IGNORECASE), "JAILBREAK_ROLEPLAY"),
    (re.compile(r"disregard\s+(?:safety|all\s+rules|moderation)", re.IGNORECASE), "SAFETY_POLICY_DISREGARD"),
    (re.compile(r"<script[\s>]|javascript:|onerror=", re.IGNORECASE), "XSS_INJECTION"),
]

# PII Patterns for redaction
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


class GuardrailReport(BaseModel):
    """Structured report returned by the guardrail evaluation pipeline."""
    passed: bool = True
    blocked: bool = False
    violations: list[str] = Field(default_factory=list)
    sanitized_items: list[str] = Field(default_factory=list)
    risk_score: float = 0.0  # 0.0 (clean) to 1.0 (blocked)
    latency_ms: float = 0.0


class CrewGuardrails:
    """Deterministic, zero-token guardrails engine for CrewAI Studio."""

    @classmethod
    def sanitize_text(cls, text: str) -> tuple[str, list[str]]:
        """Mask PII (Credit cards, SSN, Emails, Phones) from text string."""
        sanitized = text
        masked: list[str] = []

        if CREDIT_CARD_PATTERN.search(sanitized):
            sanitized = CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", sanitized)
            masked.append("CREDIT_CARD")

        if SSN_PATTERN.search(sanitized):
            sanitized = SSN_PATTERN.sub("[REDACTED_SSN]", sanitized)
            masked.append("SSN")

        if EMAIL_PATTERN.search(sanitized):
            sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
            masked.append("EMAIL")

        if PHONE_PATTERN.search(sanitized):
            sanitized = PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
            masked.append("PHONE")

        return sanitized, masked

    @classmethod
    def evaluate_inputs(cls, inputs: dict[str, Any]) -> tuple[dict[str, Any], GuardrailReport]:
        """Inspect and sanitize input payload before passing to Crew."""
        start = time.perf_counter()
        violations: list[str] = []
        sanitized_items: list[str] = []
        cleaned_inputs: dict[str, Any] = {}
        blocked = False

        for key, val in inputs.items():
            if isinstance(val, str):
                # Check for prompt injection
                for pattern, name in INJECTION_PATTERNS:
                    if pattern.search(val):
                        violations.append(f"{name} in field '{key}'")
                        blocked = True

                # Sanitize PII
                clean_val, masked = cls.sanitize_text(val)
                if masked:
                    sanitized_items.extend([f"{m} in '{key}'" for m in masked])
                cleaned_inputs[key] = clean_val
            else:
                cleaned_inputs[key] = val

        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        risk = 1.0 if blocked else (0.4 if sanitized_items else 0.0)

        report = GuardrailReport(
            passed=not blocked,
            blocked=blocked,
            violations=violations,
            sanitized_items=sanitized_items,
            risk_score=risk,
            latency_ms=latency_ms,
        )
        return cleaned_inputs, report

    @classmethod
    def evaluate_output(cls, output: str) -> tuple[str, GuardrailReport]:
        """Inspect and sanitize agent response output before returning to client."""
        start = time.perf_counter()
        clean_text, masked = cls.sanitize_text(output)
        latency_ms = round((time.perf_counter() - start) * 1000, 3)

        report = GuardrailReport(
            passed=True,
            blocked=False,
            violations=[],
            sanitized_items=masked,
            risk_score=0.2 if masked else 0.0,
            latency_ms=latency_ms,
        )
        return clean_text, report
