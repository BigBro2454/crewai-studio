# CrewAI Studio — Enterprise Visual Multi-Agent Runtime & Studio

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![CrewAI v0.11+](https://img.shields.io/badge/CrewAI-v0.11%2B-FF4B4B?style=flat)](https://crewai.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![HTMX](https://img.shields.io/badge/HTMX-2.0-3366CC?style=flat)](https://htmx.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?style=flat&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-8E75B2?style=flat&logo=googlegemini&logoColor=white)](https://aistudio.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Engineering Design Document & Production Architecture Showcase**  
> **Author:** Ishan Dhiman ([@BigBro2454](https://github.com/BigBro2454))  
> **Target Alignment:** Multi-Agent Systems Architecture / Google Cloud AI / Enterprise Autonomous Systems  
> **Repository:** [github.com/BigBro2454/crewai-studio](https://github.com/BigBro2454/crewai-studio)  
> **API Documentation:** `http://localhost:8000/api/docs` (OpenAPI / Swagger UI)

---

## 1. Executive Summary & Systems Problem Statement

While multi-agent orchestration frameworks like **CrewAI** enable complex reasoning workflows through specialized role delegation, taking multi-agent swarms from local terminal scripts to **resilient, observable enterprise applications** introduces severe operational bottlenecks:

1. **The "Black-Box Execution" Trap:** Typical multi-agent scripts execute synchronously in CLI environments. In a web runtime, a blocking agent run starves the event loop, offers zero visibility into intermediate thought loops, and fails to provide incremental feedback to users during 60+ second inference sequences.
2. **Brittle Agent Task Handoffs:** Without formal schema validation and deterministic task definitions, sequential agent chains suffer from context drift, hallucinated prerequisites, and unrecoverable downstream degradation.
3. **Vendor Lock-in & Provider Homogeneity:** Real-world enterprise systems demand heterogeneous LLM backends—leveraging fast, cost-effective models (e.g., **Google Gemini 2.5 Flash**) for high-volume data retrieval, alongside specialized reasoning models (e.g., Claude 3.5 Sonnet or GPT-4o) for high-stakes copywriting.
4. **Log Fragmentation & Telemetry:** Capturing raw standard output and formatting terminal escape codes (ANSI color sequences) into lightweight, web-safe real-time telemetry requires safe stream redirection without risking process deadlock.

**CrewAI Studio** addresses these challenges by providing an asynchronous, production-grade visual runtime built with **FastAPI**, **CrewAI**, **HTMX**, and **Tailwind CSS**. It decouples long-running multi-agent execution onto isolated worker threads, intercepts stdout via an in-memory `BufferTee` ring, and streams real-time agent reasoning steps to modern web clients via **Server-Sent Events (SSE)**.

---

## 2. High-Level Systems Architecture

The platform architecture cleanly decouples client interactions, API orchestration, in-memory state tracking, and background multi-agent execution:

```mermaid
graph TB
    subgraph ClientLayer["Client & Visual Workspace (HTMX + Tailwind)"]
        UI_Dash["Dashboard View<br/>(/)"]
        UI_Crew["Crew Studio & Runner<br/>(/crews/{name})"]
        UI_Runs["Live Run Monitor & History<br/>(/runs)"]
        SSE_Client["HTMX SSE Extension<br/>(hx-ext='sse')"]
    end

    subgraph APILayer["FastAPI Gateway & Dispatcher"]
        HTTP_Router["REST & Page Routers<br/>(FastAPI / Jinja2)"]
        BackgroundMgr["Async BackgroundTasks<br/>(Non-blocking Task Spawner)"]
        SSE_Endpoint["SSE Stream Endpoint<br/>(/api/runs/{id}/stream)"]
    end

    subgraph StateLayer["In-Memory State & Buffer Management"]
        RunStore["RunStore State Engine<br/>(Concurrent UUID -> RunResult Dict)"]
        LogBuffer["Log Ring Buffer<br/>(_log_buffers[run_id])"]
        BufferTee["BufferTee Stream Interceptor<br/>(ANSI Stripper + Stdout Tap)"]
    end

    subgraph AgentRuntime["CrewAI Execution Core (Background Worker Thread)"]
        CrewEngine["Crew Runtime Engine<br/>(asyncio.to_thread)"]
        ProcessEngine["Sequential / Hierarchical Process"]
        AgentFleet["Specialized Agent Fleet<br/>(Role, Goal, Backstory)"]
        TaskDAG["Task Execution Pipeline<br/>(Context Passing & Evaluation)"]
    end

    subgraph IntelligenceLayer["Multi-Provider LLM Factory"]
        Factory["LLM Factory<br/>(backend.config.llm_factory)"]
        GeminiLLM["Google Gemini<br/>(gemini-2.5-flash / gemini-1.5-pro)"]
        AnthropicLLM["Anthropic<br/>(claude-3-5-sonnet)"]
        OpenAILLM["OpenAI<br/>(gpt-4o)"]
    end

    subgraph ToolingLayer["Integrated Agent Tools"]
        SerperTool["SerperDevTool<br/>(Google Search API)"]
        BrowserTool["Browserless<br/>(Headless Web Scraper)"]
    end

    %% Wiring
    UI_Dash --> HTTP_Router
    UI_Crew --> HTTP_Router
    UI_Runs --> HTTP_Router
    UI_Crew -->|POST /api/runs (Form/JSON)| HTTP_Router

    HTTP_Router --> BackgroundMgr
    BackgroundMgr -->|Spawn async thread| CrewEngine
    HTTP_Router --> RunStore

    SSE_Client -->|EventSource GET| SSE_Endpoint
    SSE_Endpoint --> LogBuffer
    SSE_Endpoint --> RunStore

    CrewEngine --> ProcessEngine
    ProcessEngine --> AgentFleet
    AgentFleet --> TaskDAG
    TaskDAG --> ToolingLayer

    CrewEngine --> BufferTee
    BufferTee --> LogBuffer

    AgentFleet --> Factory
    Factory --> GeminiLLM
    Factory --> AnthropicLLM
    Factory --> OpenAILLM
```

---

## 3. CrewAI Multi-Agent Hierarchy Blueprints

### Blueprint A: Research Crew (3-Tier Specialist Pipeline)
Designed for deep investigative synthesis, this crew employs a strict separation of concerns across discovery, qualitative analysis, and publication:

```mermaid
graph LR
    subgraph Inputs["Input Ingestion"]
        Topic["User Topic Input<br/>{topic}"]
    end

    subgraph SpecialistCrew["Research Crew Specialists"]
        A_Research["Senior Research Specialist<br/><b>Goal:</b> Exhaustive data collection<br/><b>Tools:</b> SerperDevTool / Web Search"]
        A_Analyst["Data Analyst<br/><b>Goal:</b> Distill raw sources<br/><b>Focus:</b> Pattern synthesis & takeaways"]
        A_Writer["Technical Writer<br/><b>Goal:</b> Publication-grade report<br/><b>Format:</b> Clean Markdown"]
    end

    subgraph TaskPipeline["Sequential Task Pipeline"]
        T1["Task 1: Deep Research<br/><i>Expected: Bulleted facts & sources</i>"]
        T2["Task 2: Data Analysis<br/><i>Expected: Numbered analytical insights</i>"]
        T3["Task 3: Report Synthesis<br/><i>Expected: Structured markdown doc</i>"]
    end

    subgraph Output["Verified Deliverable"]
        Report["Executive Research Report<br/>(Intro, Findings, Insights, Conclusion)"]
    end

    Topic --> A_Research
    A_Research --> T1
    T1 -->|Raw Sources & Fact Dump| A_Analyst
    A_Analyst --> T2
    T2 -->|Structured Analytical Insights| A_Writer
    A_Writer --> T3
    T3 --> Report
```

---

### Blueprint B: Content Strategy Crew (Collaborative Brief & Copywriting)
Optimized for multi-format marketing generation, aligning strategic audience personas with tailored copy:

```mermaid
graph TD
    subgraph ClientParams["Campaign Parameters"]
        C_Topic["Topic: {topic}"]
        C_Audience["Audience: {audience}"]
        C_Type["Content Type: {content_type}"]
    end

    subgraph ContentCrewMembers["Content Specialist Pair"]
        Strategist["Content Strategist<br/><b>Role:</b> Audience profiling & narrative architecture<br/><b>Backstory:</b> Seasoned strategist crafting high-converting briefs"]
        Copywriter["Senior Copywriter<br/><b>Role:</b> High-impact messaging & drafting<br/><b>Backstory:</b> Award-winning writer converting briefs into viral copy"]
    end

    subgraph ExecutionHandoff["Deterministic Task Handoff"]
        Brief["Task 1: Content Strategy Plan<br/>• Headline Variations<br/>• Core Narrative Pillars<br/>• Tone of Voice & Audience Hook"]
        FinalCopy["Task 2: Publication Copywriting<br/>• Markdown Formatted Deliverable<br/>• Audience-tailored Call-to-Action"]
    end

    ClientParams --> Strategist
    Strategist --> Brief
    Brief -->|Structured Strategic Brief| Copywriter
    Copywriter --> FinalCopy
```

---

### Sequence C: Non-Blocking SSE Streaming & Output Rendering Lifecycle
Demonstrates how raw standard output generated inside deep CrewAI worker threads is captured, sanitized, streamed, and rendered:

```mermaid
sequenceDiagram
    autonumber
    participant Client as Web Browser (HTMX)
    participant API as FastAPI Router (/api/runs)
    participant Store as RunStore (State)
    participant Worker as Background Thread (asyncio.to_thread)
    participant Tee as BufferTee & ANSI Stripper
    participant Crew as CrewAI Execution Runtime
    participant SSE as SSE Stream Endpoint

    Client->>API: POST /api/runs (crew_name="research", inputs={...})
    API->>Store: Create RunResult(status="pending", run_id=UUID)
    API->>Worker: Dispatch _execute_crew(run_id, crew_name, inputs)
    API-->>Client: 202 Accepted (Render active_run.html + connect SSE)

    Client->>SSE: GET /api/runs/{run_id}/stream (EventSource)
    activate SSE

    Worker->>Store: Update status: RUNNING
    Worker->>Tee: Swap sys.stdout / sys.stderr with BufferTee

    loop Agent Reasoning & Tool Calls
        Crew->>Tee: print("Thought: Searching for sources...")
        Tee->>Tee: Strip ANSI escape codes & strip whitespace
        Tee->>Store: Append to _log_buffers[run_id]
        SSE->>Client: event: message, data: "Searching for sources..."
        Client->>Client: Append line to #log-output & autoscroll
    end

    Crew-->>Worker: CrewOutput(raw="## Research Report...")
    Worker->>Tee: Restore original sys.stdout / sys.stderr
    Worker->>Store: Update status: COMPLETED, output=raw_markdown
    Worker->>Store: Append "__DONE__" sentinel to buffer

    SSE->>Client: event: status, data: '<span class="badge">Completed</span>'
    SSE->>Client: event: done, data: '<div class="output">Rendered HTML</div>'
    deactivate SSE
```

---

## 4. Crew Specifications & Task Execution Matrix

| Crew Identifier | Specialist Agent | Model Role & Goal | Assigned Task & Expected Output | Environmental Tools |
| :--- | :--- | :--- | :--- | :--- |
| **`research`** | **Senior Research Specialist** | Find comprehensive, fact-checked data on `{topic}`. | **`research_task`**: Bullet-point summary of key facts, historical precedents, and sources. | `SerperDevTool` (Google Search) |
| | **Data Analyst** | Analyze findings, identify quantitative trends, and extract key takeaways. | **`analysis_task`**: Analytical breakdown with numbered insights and cross-domain implications. | None (Pure Reasoning) |
| | **Technical Writer** | Synthesize complex findings into an executive-ready report. | **`writing_task`**: Polished Markdown document with executive summary, findings, and conclusion. | Markdown Parser |
| **`content`** | **Content Strategist** | Architect a strategic content brief for `{topic}` targeting `{audience}`. | **`strategy_task`**: Outline with headline variants, core messaging pillars, and recommended tone. | None (Strategic Analysis) |
| | **Senior Copywriter** | Produce publication-ready `{content_type}` matching the strategy brief. | **`writing_task`**: Final draft complete with audience hooks and formatted calls-to-action. | Markdown Formatter |

---

## 5. L5 Systems & Architectural Trade-off Matrix

| Architecture Dimension | Strategy A | Strategy B | Selected Recommendation & Production Rationale |
| :--- | :--- | :--- | :--- |
| **Agent Process Model** | **Sequential Execution (`Process.sequential`)**<br/>• Deterministic data flow<br/>• High predictability<br/>• Linear latency $O(N)$ | **Hierarchical Swarm (`Process.hierarchical`)**<br/>• Dynamic manager delegation<br/>• Higher reasoning autonomy<br/>• Risk of delegation loops & extra LLM overhead | **Sequential by Default**: Guarantees deterministic task pipelines for research and content generation while eliminating infinite delegation loops. |
| **Telemetry Interception** | **Direct Stdout Tap (`BufferTee`)**<br/>• Zero framework changes<br/>• Universal support for all third-party libraries | **Structured Event Bus (OpenTelemetry)**<br/>• Strict event schemas<br/>• Requires custom SDK hooks across all agent internals | **Hybrid BufferTee**: Captures raw terminal outputs with regex ANSI sanitization for real-time SSE streaming without intrusive monkeypatching. |
| **State Storage Strategy** | **In-Memory Store (`run_store.py`)**<br/>• Zero operational dependencies<br/>• Sub-millisecond read/write latency<br/>• Ephemeral across restarts | **Distributed Datastore (PostgreSQL / Redis)**<br/>• Durable state persistence<br/>• Horizontal multi-node scaling<br/>• Network latency & schema management | **In-Memory for Studio Sandbox**: Keeps setup instantaneous (`setup.sh`) with clean interfaces prepared for drop-in Redis/SQLAlchemy backend extension. |
| **Inference Routing** | **Uniform Model (e.g. all GPT-4o)**<br/>• High consistency<br/>• Sub-optimal compute cost allocation | **Multi-Provider Factory (`llm_factory.py`)**<br/>• Per-agent / per-environment model configuration<br/>• Multi-cloud redundancy | **Multi-Provider Factory**: Enables routing research tasks to cost-effective **Gemini 2.5 Flash** and synthesis tasks to Claude 3.5 Sonnet. |

---

## 6. Production Guardrails & Failure Recovery

1. **ANSI Code Sanitization:**
   - Agent outputs generated via Rich or colorized terminals contain raw ANSI control sequences (e.g., `\x1B[32m`). The `BufferTee` applies pre-compiled regex filters (`re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")`) before queueing strings into SSE buffers, preventing HTML corruption.
2. **Worker Thread Isolation:**
   - Long-running inference processes are wrapped in `asyncio.to_thread(_run)` rather than executed in the main event loop, ensuring FastAPI remains 100% responsive to incoming health checks, SSE handshakes, and UI navigation.
3. **Graceful Degraded Tooling:**
   - Web search tools (`SerperDevTool`) verify both module availability (`_HAS_SERPER`) and credentials (`SERPER_API_KEY`) at runtime. If absent, the crew gracefully falls back to parametric LLM knowledge without crashing.
4. **Sentinel Stream Termination:**
   - Every background execution safely appends a `__DONE__` sentinel to the log ring buffer in a `finally` block, ensuring client-side SSE connections cleanly terminate without hanging.

---

## 7. Quickstart & Installation

### Prerequisites
- **Python 3.11** or higher
- An API Key for your preferred provider (**Google Gemini**, OpenAI, or Anthropic)

### 1. Automated Setup
The included setup script prepares the virtual environment, installs development dependencies, and creates your `.env` configuration:
```bash
bash scripts/setup.sh
```

Alternatively, install manually using `pip`:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### 2. Configure Credentials
Edit `.env` and set your primary LLM credentials:
```bash
# Recommended: Google Gemini
DEFAULT_LLM_PROVIDER=google
GOOGLE_API_KEY="AIzaSy..."
GEMINI_MODEL="gemini-2.5-flash"
```

### 3. Run Tests
Verify system integrity and API route registration:
```bash
source .venv/bin/activate
pytest
```
*Expected: 8 passed across unit, API, and page route suites.*

### 4. Start CrewAI Studio
```bash
python main.py
# Server starts at: http://0.0.0.0:8000
```

Open your browser to **`http://localhost:8000`** to access the visual studio!

---

## 8. REST & Streaming API Reference

| Method | Endpoint | Description | Payload / Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/crews` | List all registered crews & configurations | `list[CrewConfig]` |
| `GET` | `/api/crews/{name}` | Retrieve schema for a specific crew | `CrewConfig` |
| `POST` | `/api/runs` | Launch a new crew run asynchronously | `{"crew_name": "research", "inputs": {"topic": "AI Agents"}}` $\to$ `202 Accepted` |
| `GET` | `/api/runs` | Retrieve execution history for all runs | `list[RunResult]` |
| `GET` | `/api/runs/{run_id}` | Inspect status and output of a specific run | `RunResult` |
| `GET` | `/api/runs/{run_id}/stream` | **Server-Sent Events (SSE)** log stream | `text/event-stream` (`message`, `status`, `done`) |

---

## 9. Repository Structure

```
crewai-studio/
├── .env.example                    # Safe template for credentials
├── .gitignore                      # Zero-leak Git exclusion rules
├── LICENSE                         # MIT Open Source License
├── main.py                         # Application entrypoint & Uvicorn runner
├── pyproject.toml                  # PEP 517/621 packaging metadata & dev dependencies
├── README.md                       # L5 Systems Architecture & Design Document
├── scripts/
│   └── setup.sh                    # Automated dev setup script
├── tests/
│   └── test_crews.py               # Comprehensive pytest test suite
│
├── backend/
│   ├── api/
│   │   ├── app.py                  # FastAPI application & UI route registration
│   │   └── routers/
│   │       ├── crews.py            # Crew metadata endpoints
│   │       └── runs.py             # Run execution & SSE streaming endpoints
│   ├── config/
│   │   ├── llm_factory.py          # Multi-provider LLM factory (Gemini, Claude, GPT)
│   │   └── settings.py             # Pydantic BaseSettings management
│   ├── crews/
│   │   ├── __init__.py             # Crew registry & dynamic factory
│   │   ├── content_crew.py         # Strategist + Copywriter collaborative crew
│   │   └── research_crew.py        # Researcher + Analyst + Writer pipeline crew
│   ├── models/
│   │   └── schemas.py              # Pydantic schemas (CrewConfig, RunResult, Status)
│   └── utils/
│       └── run_store.py            # Thread-safe in-memory run store
│
└── ui/
    ├── static/                     # CSS / JS static assets
    └── templates/
        ├── base.html               # Master layout & sidebar navigation
        ├── index.html              # Studio dashboard & metrics
        ├── crews/
        │   ├── detail.html         # Crew execution form & live stream monitor
        │   └── runs.html           # Historical run table & status log
        └── partials/               # Reusable HTMX server-rendered components
            ├── active_run.html     # Active run card with SSE listener
            ├── crew_detail.html    # Crew configuration viewer
            └── runs_list.html      # Dynamic run table fragment
```

---

## 10. License & Attributions

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for details.  
Engineered with [CrewAI](https://crewai.com), [FastAPI](https://fastapi.tiangolo.com), and [HTMX](https://htmx.org) by [Ishan Dhiman](https://github.com/BigBro2454).
