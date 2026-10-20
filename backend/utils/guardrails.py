"""Multi-stage security guardrails, rate limiting, and PII/credential masking for CrewAI Studio."""
from __future__ import annotations

import re
import threading
import time
from typing import Any
from pydantic import BaseModel, Field


# ── Guardrail Patterns ────────────────────────────────────────────────────────

INJECTION_PATTERNS = [
    (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?", re.IGNORECASE), "PROMPT_INJECTION_IGNORE_INSTRUCTIONS"),
    (re.compile(r"system\s+(?:prompt|override|directive)\s+bypass", re.IGNORECASE), "SYSTEM_PROMPT_OVERRIDE"),
    (re.compile(r"(?:you\s+are\s+now|act\s+as)\s+(?:DAN|jailbreak|unfiltered\s+AI)", re.IGNORECASE), "JAILBREAK_ROLEPLAY"),
    (re.compile(r"disregard\s+(?:safety|all\s+rules|moderation)", re.IGNORECASE), "SAFETY_POLICY_DISREGARD"),
    (re.compile(r"(?:show|print|reveal|leak|output)\s+(?:me\s+)?(?:the\s+)?(?:system\s+prompt|developer\s+instructions?|secret\s+keys?)", re.IGNORECASE), "PROMPT_EXTRACTION"),
    (re.compile(r"<script[\s>]|javascript:|onerror=", re.IGNORECASE), "XSS_INJECTION"),
]

# PII Patterns for redaction
CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

# Credential Suppression Patterns (Zero-Leak Security Protocol)
GEMINI_KEY_PATTERN = re.compile(r"\bAIzaSy[A-Za-z0-9_-]{30,40}\b")
OPENAI_KEY_PATTERN = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")
ANTHROPIC_KEY_PATTERN = re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")
GITHUB_PAT_PATTERN = re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,45}\b")
BEARER_TOKEN_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}", re.IGNORECASE)


# ── Rate Limiter ─────────────────────────────────────────────────────────────

class TokenBucketRateLimiter:
    """Thread-safe Token Bucket Rate Limiter preventing runaway loops and denial-of-wallet thrashing."""

    def __init__(self, capacity: int = 60, refill_rate: float = 2.0):
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)  # tokens per second
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> tuple[bool, float, float]:
        """
        Attempt to acquire tokens.
        Returns: (allowed, remaining_tokens, wait_seconds)
        """
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, round(self.tokens, 2), 0.0

            needed = tokens - self.tokens
            wait_time = needed / self.refill_rate if self.refill_rate > 0 else 0.0
            return False, round(self.tokens, 2), round(wait_time, 2)

    def reset(self) -> None:
        """Reset the rate limiter bucket to full capacity."""
        with self._lock:
            self.tokens = self.capacity
            self.last_refill = time.monotonic()


# Default singleton instance
_GLOBAL_RATE_LIMITER = TokenBucketRateLimiter(capacity=60, refill_rate=2.0)


# ── Structured Reports ───────────────────────────────────────────────────────

class GuardrailReport(BaseModel):
    """Structured report returned by the guardrail evaluation pipeline."""
    passed: bool = True
    blocked: bool = False
    violations: list[str] = Field(default_factory=list)
    sanitized_items: list[str] = Field(default_factory=list)
    redacted_credentials: list[str] = Field(default_factory=list)
    rate_limit_allowed: bool = True
    financial_approved: bool = True
    risk_score: float = 0.0  # 0.0 (clean) to 1.0 (blocked)
    latency_ms: float = 0.0


# ── Guardrails Engine ────────────────────────────────────────────────────────

class CrewGuardrails:
    """Deterministic, zero-token defense-in-depth guardrails engine for CrewAI Studio."""

    rate_limiter: TokenBucketRateLimiter = _GLOBAL_RATE_LIMITER

    @classmethod
    def sanitize_credentials(cls, text: str) -> tuple[str, list[str]]:
        """Mask API keys and authentication tokens before transmission or logging."""
        sanitized = text
        masked: list[str] = []

        if GEMINI_KEY_PATTERN.search(sanitized):
            sanitized = GEMINI_KEY_PATTERN.sub("[REDACTED_GEMINI_KEY]", sanitized)
            masked.append("GEMINI_KEY")

        if OPENAI_KEY_PATTERN.search(sanitized):
            sanitized = OPENAI_KEY_PATTERN.sub("[REDACTED_OPENAI_KEY]", sanitized)
            masked.append("OPENAI_KEY")

        if ANTHROPIC_KEY_PATTERN.search(sanitized):
            sanitized = ANTHROPIC_KEY_PATTERN.sub("[REDACTED_ANTHROPIC_KEY]", sanitized)
            masked.append("ANTHROPIC_KEY")

        if GITHUB_PAT_PATTERN.search(sanitized):
            sanitized = GITHUB_PAT_PATTERN.sub("[REDACTED_GITHUB_TOKEN]", sanitized)
            masked.append("GITHUB_PAT")

        if BEARER_TOKEN_PATTERN.search(sanitized):
            sanitized = BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED_BEARER_TOKEN]", sanitized)
            masked.append("BEARER_TOKEN")

        return sanitized, masked

    @classmethod
    def sanitize_text(cls, text: str) -> tuple[str, list[str]]:
        """Mask PII (Credit cards, SSN, Emails, Phones) and Credentials from text string."""
        sanitized = text
        masked: list[str] = []

        # 1. PII Redaction
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

        # 2. Credential Redaction
        sanitized, creds = cls.sanitize_credentials(sanitized)
        masked.extend(creds)

        return sanitized, masked

    @classmethod
    def evaluate_budget_limit(cls, amount: float, threshold: float = 500.0) -> tuple[bool, str]:
        """Programmatic financial boundary evaluation enforcing spending caps."""
        if amount > threshold:
            return False, f"Budget limit exceeded: ${amount:.2f} exceeds auto-approval ceiling of ${threshold:.2f} (HITL Escalation Required)"
        return True, f"Budget approved: ${amount:.2f} within threshold ${threshold:.2f}"

    @classmethod
    def check_rate_limit(cls, tokens: int = 1) -> tuple[bool, float, float]:
        """Check rate limiter quota without blocking."""
        return cls.rate_limiter.acquire(tokens)

    @classmethod
    def evaluate_inputs(cls, inputs: dict[str, Any]) -> tuple[dict[str, Any], GuardrailReport]:
        """Inspect and sanitize input payload before passing to Crew."""
        start = time.perf_counter()
        violations: list[str] = []
        sanitized_items: list[str] = []
        redacted_creds: list[str] = []
        cleaned_inputs: dict[str, Any] = {}
        blocked = False
        financial_approved = True

        # Check rate limiter
        rl_allowed, remaining, wait_time = cls.check_rate_limit(1)
        if not rl_allowed:
            violations.append(f"RATE_LIMIT_EXCEEDED (Bucket depleted, wait {wait_time:.1f}s)")
            blocked = True

        for key, val in inputs.items():
            if isinstance(val, (int, float)) and key.lower() in ("budget", "amount", "cost", "spending_cap"):
                approved, msg = cls.evaluate_budget_limit(float(val), threshold=500.0)
                if not approved:
                    financial_approved = False
                    violations.append(msg)
                    blocked = True
                cleaned_inputs[key] = val
            elif isinstance(val, str):
                # Check for prompt injection
                for pattern, name in INJECTION_PATTERNS:
                    if pattern.search(val):
                        violations.append(f"{name} in field '{key}'")
                        blocked = True

                # Sanitize PII & Credentials
                clean_val, masked = cls.sanitize_text(val)
                if masked:
                    for m in masked:
                        if m in ("GEMINI_KEY", "OPENAI_KEY", "ANTHROPIC_KEY", "GITHUB_PAT", "BEARER_TOKEN"):
                            redacted_creds.append(f"{m} in '{key}'")
                        sanitized_items.append(f"{m} in '{key}'")
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
            redacted_credentials=redacted_creds,
            rate_limit_allowed=rl_allowed,
            financial_approved=financial_approved,
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

        redacted_creds = [m for m in masked if m in ("GEMINI_KEY", "OPENAI_KEY", "ANTHROPIC_KEY", "GITHUB_PAT", "BEARER_TOKEN")]

        report = GuardrailReport(
            passed=True,
            blocked=False,
            violations=[],
            sanitized_items=masked,
            redacted_credentials=redacted_creds,
            rate_limit_allowed=True,
            financial_approved=True,
            risk_score=0.2 if masked else 0.0,
            latency_ms=latency_ms,
        )
        return clean_text, report
