"""Deterministic offline mock execution engine for CrewAI Studio."""
from __future__ import annotations

import asyncio
from typing import Any


class MockCrewEngine:
    """Simulates realistic multi-agent execution loops with zero token spend."""

    @classmethod
    async def execute_mock(
        cls,
        crew_name: str,
        inputs: dict[str, Any],
        buffer: list[str],
        step_delay: float = 0.05,
    ) -> str:
        """Run simulated agent reasoning and stream logs into the provided buffer."""
        name = crew_name.lower()
        if name == "research":
            return await cls._run_research(inputs, buffer, step_delay)
        elif name == "content":
            return await cls._run_content(inputs, buffer, step_delay)
        elif name == "governance":
            return await cls._run_governance(inputs, buffer, step_delay)
        else:
            return await cls._run_generic(crew_name, inputs, buffer, step_delay)

    @classmethod
    async def _emit(cls, buffer: list[str], message: str, delay: float) -> None:
        buffer.append(message)
        if delay > 0:
            await asyncio.sleep(delay)

    @classmethod
    async def _run_research(cls, inputs: dict[str, Any], buffer: list[str], delay: float) -> str:
        topic = inputs.get("topic", "Autonomous Multi-Agent Systems")
        focus = inputs.get("focus", "Enterprise Observability & Latency SLAs")

        await cls._emit(buffer, f"🚀 [Orchestrator] Starting Research Crew pipeline for '{topic}'...", delay)
        await cls._emit(buffer, f"🤖 [Senior Researcher] Initializing task: Comprehensive research on {topic}", delay)
        await cls._emit(buffer, f"🤔 [Senior Researcher] Thought: Need to uncover primary architectural patterns and enterprise benchmarks for {focus}.", delay)
        await cls._emit(buffer, f"🔧 [Senior Researcher] Action: SerperDevTool -> Query: '{topic} architecture benchmarks {focus}'", delay)
        await cls._emit(buffer, f"👁️ [Senior Researcher] Observation: Retrieved 8 whitepapers, arXiv preprints, and Google Cloud AI production case studies.", delay)
        await cls._emit(buffer, f"💡 [Senior Researcher] Thought: Synthesizing key findings into executive technical brief.", delay)
        await cls._emit(buffer, f"✅ [Senior Researcher] Task completed. Passing findings to Technical Analyst.", delay)

        await cls._emit(buffer, f"🤖 [Technical Analyst] Initializing task: Analyze trade-offs and latency vs cost frontiers.", delay)
        await cls._emit(buffer, f"🤔 [Technical Analyst] Thought: Quantifying Gemini 2.5 Flash token economics vs Claude 3.5 Sonnet / GPT-4o.", delay)
        await cls._emit(buffer, f"📊 [Technical Analyst] Observation: Gemini 2.5 Flash yields 95.2% cost reduction with sub-second P50 latency.", delay)
        await cls._emit(buffer, f"✅ [Technical Analyst] Task completed. Forwarding analysis matrix to Lead Writer.", delay)

        await cls._emit(buffer, f"🤖 [Lead Technical Writer] Initializing task: Synthesize final executive report in GFM Markdown.", delay)
        await cls._emit(buffer, f"✍️ [Lead Technical Writer] Thought: Formatting executive summary, architecture diagram, and recommendations.", delay)
        await cls._emit(buffer, f"🎉 [Lead Technical Writer] Final delivery complete.", delay)

        output = f"""# Executive Research Report: {topic}

## 1. Executive Summary
An exhaustive multi-agent systems review of **{topic}**, concentrating on **{focus}**. 

### Key Findings
- **Asynchronous Decoupling**: Offloading blocking multi-agent execution to isolated worker threads eliminates event-loop starvation.
- **Observable Telemetry**: Real-time log capture via in-memory ring buffers and SSE streaming achieves <100ms UI update latency.
- **Token Economics**: Leveraging Gemini 2.5 Flash delivers enterprise-grade reasoning at $0.075/1M prompt tokens (>95% savings over GPT-4o).

## 2. Architectural Trade-Offs
| Paradigm | Latency (P90) | Cost / 1k Runs | Fault Tolerance |
| :--- | :--- | :--- | :--- |
| **CrewAI Studio (FastAPI + SSE)** | **1.2s** | **$0.42** | **ACID SQLite Checkpointing** |
| Monolithic CLI Scripts | 18.5s | $6.80 | Process Crash / Zero Recovery |
| Heavyweight Microservices | 4.8s | $4.20 | Distributed Complexity |

## 3. Recommended Roadmap
1. Enforce strict pre-execution input guardrails and PII masking.
2. Standardize on dual-runtime failover for mission-critical workflows.
"""
        return output

    @classmethod
    async def _run_content(cls, inputs: dict[str, Any], buffer: list[str], delay: float) -> str:
        topic = inputs.get("topic", "AI Product Management")
        audience = inputs.get("target_audience", "Senior Tech Leaders & TPMs")

        await cls._emit(buffer, f"🚀 [Orchestrator] Starting Content Strategy Crew for '{topic}'...", delay)
        await cls._emit(buffer, f"🤖 [Content Strategist] Analyzing audience persona: {audience}", delay)
        await cls._emit(buffer, f"🤔 [Content Strategist] Thought: Formulating narrative hook around systems-level execution over buzzwords.", delay)
        await cls._emit(buffer, f"📋 [Content Strategist] Content Outline finalized: Hook -> Proof -> Architecture -> Call to Action.", delay)
        await cls._emit(buffer, f"✅ [Content Strategist] Passing brief to Senior Copywriter.", delay)

        await cls._emit(buffer, f"🤖 [Senior Copywriter] Drafting multi-platform copy campaign...", delay)
        await cls._emit(buffer, f"✍️ [Senior Copywriter] Thought: Eliminating em dashes, focusing on active voice and concrete rupee/time stakes.", delay)
        await cls._emit(buffer, f"🎉 [Senior Copywriter] Copy finalized and reviewed against brand voice standards.", delay)

        output = f"""# Content Campaign Brief: {topic}

**Target Audience:** {audience}  
**Format:** LinkedIn Long-form & Technical Newsletter  

## The Core Asset
Most AI product demos fail because they treat multi-agent swarms as black-box scripts. 

When your model takes 45 seconds to synthesize research, a spinning wheel kills user trust. 

Here is how production systems solve this:
1. Intercept standard output in real-time without deadlock.
2. Stream incremental thought loops over Server-Sent Events.
3. Persist every step into an ACID SQLite audit store.

**Result:** Zero event-loop starvation. Full transparency. 95% lower API spend.
"""
        return output

    @classmethod
    async def _run_governance(cls, inputs: dict[str, Any], buffer: list[str], delay: float) -> str:
        topic = inputs.get("topic", "Enterprise Multi-Agent Swarm Governance")
        scope = inputs.get("scope", "Zero-Leak Security, Rate Limiting & Token Economics")

        await cls._emit(buffer, f"🚀 [Orchestrator] Starting Enterprise Governance Crew for '{topic}'...", delay)
        await cls._emit(buffer, f"🤖 [Security & Policy Auditor] Initializing security audit: {scope}", delay)
        await cls._emit(buffer, f"🛡️ [Security & Policy Auditor] Thought: Inspecting input channels for PII, credential leakage, and prompt injections.", delay)
        await cls._emit(buffer, f"🔍 [Security & Policy Auditor] Action: Scan workspace credentials -> Scanned 18 files. Verified 100% zero-leak compliance.", delay)
        await cls._emit(buffer, f"✅ [Security & Policy Auditor] Compliance verified. Passing report to Systemic Risk Evaluator.", delay)

        await cls._emit(buffer, f"🤖 [Systemic Risk Evaluator] Analyzing systemic blast radius and API quota saturation...", delay)
        await cls._emit(buffer, f"🤔 [Systemic Risk Evaluator] Thought: Simulating cyclic invocation loops, token bucket rate limiting (60 burst, 2.0/s refill).", delay)
        await cls._emit(buffer, f"📊 [Systemic Risk Evaluator] Observation: Bounded recursion limits prevent denial-of-wallet thrashing; P95 latency capped at 142ms.", delay)
        await cls._emit(buffer, f"✅ [Systemic Risk Evaluator] Risk profile clean. Forwarding to Enterprise Remediation Officer.", delay)

        await cls._emit(buffer, f"🤖 [Enterprise Remediation Officer] Synthesizing governance matrix and executive scorecard...", delay)
        await cls._emit(buffer, f"📋 [Enterprise Remediation Officer] Thought: Compiling Grade A+ (100%) enterprise fleet readiness audit.", delay)
        await cls._emit(buffer, f"🎉 [Enterprise Remediation Officer] Executive Governance Scorecard published.", delay)

        output = f"""# Enterprise Multi-Agent Governance Scorecard: {topic}

**Evaluation Scope:** {scope}  
**Overall Fleet Health Rating:** **Grade A+ (100.0% Enterprise Ready)**  
**Verification Standard:** Google L5 Enterprise TPM / Systems Architecture  

---

## 1. Executive Summary
A comprehensive security, compliance, and systems risk assessment of **{topic}**. The evaluation validates defense-in-depth security guardrails, multi-provider LLM routing, deterministic rate limiting, and cross-run persistence.

### Key Governance Metrics
- **Zero-Leak Security Protocol**: 100% compliance. All active credentials (Gemini `AIzaSy`, OpenAI `sk`, Anthropic `sk-ant`, GitHub PAT) intercepted pre-transmission.
- **Denial-of-Wallet Defense**: TokenBucketRateLimiter (60 token burst capacity, 2.0 tokens/sec refill) prevents cyclic token sprawl.
- **Financial Boundary Gating**: Programmatic enforcement with $500 auto-approval ceiling and mandatory supervisor escalation.
- **Token Economics**: Vertex AI Gemini 2.5 Flash deployment achieves **97.3% cost reduction** compared to monolithic GPT-4o architectures.

---

## 2. Dimensional Audit Breakdown
| Dimension | Audit Criteria | Score | Status |
| :--- | :--- | :---: | :---: |
| **Topology & Process** | Role clarity, deterministic task DAG, sequential execution | 100 / 100 | **PASS** |
| **Provider Heterogeneity** | Multi-model routing (Google, Anthropic, OpenAI) | 100 / 100 | **PASS** |
| **Zero-Leak Security** | Pre-transmission regex masking, credential isolation | 100 / 100 | **PASS** |
| **Latency SLA** | Sub-150ms P95 latency guarantee across workloads | 100 / 100 | **PASS** |
| **Offline Determinism** | Headless mock execution without external API dependencies | 100 / 100 | **PASS** |
| **Persistence & Telemetry** | ACID SQLite session history, JSON/Markdown exporter | 100 / 100 | **PASS** |

---

## 3. Recommended Operational Safeguards
1. Enforce automated pre-commit secret scans across all developer environments.
2. Maintain token bucket rate limiting on public-facing multi-agent endpoints.
3. Leverage Vertex AI prompt caching for repeated agent context trees.
"""
        return output

    @classmethod
    async def _run_generic(cls, crew_name: str, inputs: dict[str, Any], buffer: list[str], delay: float) -> str:
        await cls._emit(buffer, f"🚀 [Orchestrator] Initializing generic mock execution for crew '{crew_name}'...", delay)
        await cls._emit(buffer, f"⚙️ [Agent] Executing with inputs: {inputs}", delay)
        await cls._emit(buffer, f"✅ [Agent] Completed generic execution.", delay)
        return f"# Run Result: {crew_name.title()}\n\nCompleted successfully with inputs: {inputs}"
