# Technical Strategy & Implementation Plan: Autonomous Idea & Prototype Generator Agent System

## 1. Executive Summary & System Overview

The **Autonomous Idea & Prototype Generator Agent System (5-Day Agent)** is a dual-tier, multi-agent architecture designed to autonomously discover market opportunities, conduct market research, synthesize product concepts, and generate working React prototype applications on an hourly schedule.

### Core Stack Strategy
- **Backend Orchestration**: Python 3.11+ using the **Google Agent Developer Kit (ADK)** and Vertex AI Agent Engine session primitives.
- **Backend API & Streaming Server**: FastAPI with WebSockets/SSE for real-time telemetry streaming and background job control.
- **Frontend Dashboard**: TypeScript, React, and Vanilla CSS delivering a modern entrepreneur dashboard with real-time agent trace streaming, interactive startup cards, source code browsing, and live iframe prototype previewing.
- **Generated Application Sandbox**: Isolated local filesystem storage (`/generated-apps/<project-id>/`) served via dynamic static preview endpoints.

---

## 2. Architectural Blueprint & Data Flow

### 2.1 Sequential Multi-Agent Pipeline Diagram

```mermaid
flowchart TD
    subgraph Scheduler & Control
        A[Top-of-the-Hour Cron Scheduler] -->|Trigger| B[Pipeline Controller]
        C[UI Start/Stop Controls] -->|Enable/Pause| A
    end

    subgraph Agent Pipeline (Google ADK Python)
        B --> D[1. Discovery Agent]
        D -->|DiscoveryResult| E[2. Market Research Agent]
        E -->|MarketResearchReport| F[3. Ideation Agent]
        F -->|ProductSpec| G[4. Implementation Agent]
        G -->|WebDev File Writer Tool| H[/generated-apps/<project-id>/]
        G -->|AppBuildArtifact| I[Pipeline Result Aggregator]
    end

    subgraph Telemetry & Observability
        D -.->|Trace Events| T[WebSocket Broadcaster]
        E -.->|Trace Events| T
        F -.->|Trace Events| T
        G -.->|Trace Events| T
    end

    subgraph Frontend Dashboard (TypeScript)
        T -->|Real-time Stream| J[Agent Trace Feed]
        I -->|Publish Startup Package| K[Startup Card Feed]
        H -->|Serve App| L[Embedded Live Iframe / Code Viewer]
    end
```

---

## 3. Data Schemas & Inter-Agent Interfaces

All communication between pipeline agents and frontend consumers follows strict typed JSON specifications.

### 3.1 `DiscoveryResult`
- `project_id`: String (UUID v4)
- `timestamp`: String (ISO 8601)
- `target_industry`: String
- `uncovered_pain_point`: String
- `target_demographic`: String
- `opportunity_score`: Float (1.0 - 10.0)
- `search_queries_used`: Array of Strings

### 3.2 `MarketResearchReport`
- `project_id`: String
- `competitors`: Array of Objects (`name`, `url`, `key_weakness`, `market_share_estimate`)
- `market_size_tam`: String
- `market_size_sam`: String
- `key_market_trends`: Array of Strings
- `target_persona_insights`: String
- `differentiation_angle`: String

### 3.3 `ProductSpec`
- `project_id`: String
- `app_name`: String
- `tagline`: String
- `value_proposition`: String
- `core_feature_list`: Array of Objects (`feature_name`, `description`, `priority`)
- `ui_ux_requirements`: Object (`color_palette`, `layout_style`, `typography_vibe`)
- `data_model_sketch`: Array of Strings

### 3.4 `AppBuildArtifact`
- `project_id`: String
- `workspace_path`: String
- `live_preview_url`: String
- `file_manifest`: Array of Objects (`file_path`, `file_size_bytes`, `file_type`)
- `build_status`: String (`SUCCESS`, `PARTIAL`, `FAILED`)
- `generation_time_seconds`: Float

### 3.5 `TraceEvent` (Telemetry Payload)
- `event_id`: String
- `project_id`: String
- `agent_name`: String (`Discovery`, `MarketResearch`, `Ideation`, `Implementation`)
- `event_type`: String (`THOUGHT`, `TOOL_QUERY`, `TOOL_EXECUTION`, `STATUS_CHANGE`)
- `content`: String
- `timestamp`: String (ISO 8601)

---

## 4. Subsystem Technical Strategy

### 4.1 Backend Engine (Python + ADK)

1. **Discovery Agent**:
   - Equiped with custom Google Search API wrapper tool.
   - Prompt strategy: Instructed to scan random combinations of modern industries (e.g., PropTech, ClimateTech, AI Micro-SaaS, Biohacking Logistics) and uncover unserved niches.
2. **Market Research Agent**:
   - Equiped with custom Google Search API wrapper tool.
   - Prompt strategy: Synthesizes direct market data, competitor gaps, TAM estimates, and demographic profiles.
3. **Ideation Agent**:
   - Zero-tool LLM agent specialized in functional product design.
   - Prompt strategy: Formulates high-converting product specs and detailed UI blueprints tailored for single-page React prototypes.
4. **Implementation Agent**:
   - Equiped with custom `WebDevFileWriter` tool.
   - Prompt strategy: Translates `ProductSpec` into valid React/JSX code, CSS design tokens, HTML scaffolding, and component layout.

### 4.2 WebDev File Writer Tool Design
- Capabilities:
  - `create_workspace_directory(project_id)`: Initializes `/generated-apps/<project-id>/`.
  - `write_file(project_id, relative_path, content)`: Creates or updates file content safely.
  - `scaffold_base_template(project_id)`: Writes default `index.html`, package manifest, and entry script.
  - `generate_manifest(project_id)`: Scans workspace directory and outputs indexable JSON manifest.

### 4.3 Session & Context Management Strategy
- Leverage native ADK Session State objects (`adk.SessionState`) passed through the sequential pipeline execution thread.
- Store step outputs directly in state keys (`state["discovery"]`, `state["market_research"]`, `state["product_spec"]`, `state["app_artifact"]`).
- Enable state recovery so paused runs can resume from the last successful agent step.

### 4.4 Scheduler & Execution Guard
- **APScheduler Engine**: Runs an hourly cron worker on the top of every hour (`0 * * * *`).
- **State Toggle**: Thread-safe global boolean flag (`is_pipeline_active`). When `False`, scheduled triggers skip execution.
- **On-Demand Execution**: Endpoint allowing manual trigger regardless of schedule status.

### 4.5 Real-Time Telemetry & Event Streaming
- Intercept ADK tool execution hooks and LLM callback events.
- Stream events instantly over FastAPI WebSockets (`/ws/trace`).
- Support log persistence to disk (`/logs/pipeline_traces.jsonl`) for historic playback.

### 4.6 Frontend Dashboard Strategy (TypeScript + React)
- **State Management**: Zustand or React Context handling WebSocket event subscriptions and active startup cards.
- **Live Agent Trace Drawer**: Visual timeline showing streaming thoughts, search terms, and file generation progress with agent status indicators.
- **Startup Card Feed**: Modern grid layout presenting generated startup packages with metadata tags, problem breakdown, market insights, feature list, and action controls.
- **Interactive App Viewer & Code Inspector**:
  - **Live Tab**: Embedded `<iframe>` pointing to backend static preview URL (`http://localhost:8000/preview/<project-id>/`).
  - **Code Tab**: Interactive directory tree with syntax-highlighted file content viewer.

---

## 5. Phase-by-Phase Implementation Roadmap

### Phase 1: Foundation & Project Workspace Setup
- **Goal**: Initialize clean directory structure, configure python ADK dependencies, and scaffold the TypeScript frontend.
- **Tasks**:
  - Establish workspace directories: `/backend/`, `/frontend/`, `/generated-apps/`, `/logs/`.
  - Configure Python virtual environment with ADK, FastAPI, Uvicorn, APScheduler, and Google Search API libraries.
  - Initialize TypeScript frontend using React + Vite + Vanilla CSS design system.
  - Define root schemas and shared TypeScript types matching Python Pydantic models.

### Phase 2: Python ADK Multi-Agent Pipeline & Custom Tools
- **Goal**: Implement the 4-agent sequential workflow and custom tool integration.
- **Tasks**:
  - Construct Google Search API tool wrapper with rate-limiting and query cleaning.
  - Build `WebDevFileWriter` tool with local filesystem sandbox security rules.
  - Configure Discovery Agent prompt templates and output schema enforcers.
  - Configure Market Research Agent prompt templates and competitor analysis parser.
  - Configure Ideation Agent prompt templates for React UI blueprinting.
  - Configure Implementation Agent prompt templates for multi-file React component writing.
  - Wire agents sequentially using ADK pipeline runner and native session state.

### Phase 3: Backend API, Scheduler & Telemetry Broadcaster
- **Goal**: Build background scheduler, control API endpoints, and WebSocket real-time trace stream.
- **Tasks**:
  - Implement FastAPI application server with CORS and error handling.
  - Add start/stop scheduler endpoints (`/api/pipeline/start`, `/api/pipeline/stop`, `/api/pipeline/status`).
  - Add manual trigger endpoint (`/api/pipeline/run-now`).
  - Integrate APScheduler hourly cron process with thread-safe execution guard.
  - Build WebSocket manager (`/ws/trace`) and tap ADK agent callbacks to broadcast `TraceEvent` objects.
  - Implement dynamic static asset mounting (`/preview/<project-id>/`) to serve generated React app sandboxes directly.

### Phase 4: TypeScript Dashboard & Real-Time Telemetry Interface
- **Goal**: Build the user dashboard, real-time agent trace viewer, and control panel.
- **Tasks**:
  - Design UI header with live status indicators, next execution countdown, and Start/Stop toggle button.
  - Build real-time Agent Trace Feed component subscribing to WebSocket streams with auto-scroll and filter capabilities.
  - Build Startup Card Feed displaying structured startup packages with industry badges, TAM estimates, and concept highlights.
  - Create card filter/search functionality by industry, date, or opportunity score.

### Phase 5: Live App Preview & Code Viewer Subsystem
- **Goal**: Enable embedded live iframe previewing and source code inspection for generated prototypes.
- **Tasks**:
  - Create interactive modal / preview panel with dual-tab interface (`Live Preview` vs `Source Code`).
  - Implement responsive `<iframe>` container pointing to `/preview/<project-id>/index.html`.
  - Build source code file browser displaying directory tree and highlighted file content viewer.
  - Add error boundary and fallback UI for incomplete or broken prototype builds.

### Phase 6: E2E Integration, Evaluation Alignment & Hardening
- **Goal**: Validate pipeline end-to-end, verify all 5 rubric criteria, and perform system hardening.
- **Tasks**:
  - Execute full end-to-end automated run from Discovery through to React prototype generation and iframe render.
  - Test start/stop scheduler state transitions and manual override controls.
  - Verify real-time streaming reliability over extended runs.
  - Perform audit against the 95-Point Evaluation Matrix.

---

## 6. Evaluation Criteria Mapping (95 Points Max)

| Evaluation Area | Target Points | Technical Implementation Proof |
| :--- | :--- | :--- |
| **1. Tool & Interface Design** | 20 pts | Google Search API tool integration in Discovery/Research agents; custom `WebDevFileWriter` tool in Implementation agent; TypeScript UI with live iframe app preview & code viewer. |
| **2. Context & Memory** | 20 pts | Sequential typed data flow (`DiscoveryResult` → `MarketResearchReport` → `ProductSpec` → `AppBuildArtifact`) using native Google ADK session state. |
| **3. Orchestration & Logic** | 20 pts | Deterministic 4-agent sequential workflow managed via Google ADK pipeline engine; top-of-the-hour background APScheduler with UI start/stop toggle. |
| **4. Observability & Tracing** | 20 pts | Real-time WebSocket streaming of agent thoughts, tool calls, search queries, and file writes, rendered in live visual trace feed. |
| **5. Infrastructure & CI/CD** | 15 pts | Clean modular directory structure separating Python ADK backend (`/backend`), TypeScript UI (`/frontend`), generated project workspace (`/generated-apps`), and log persistence (`/logs`). |

---

## 7. Technical Risk Analysis & Mitigation Strategies

### 7.1 Risk: Generated React Prototype Runtime Errors
- **Mitigation**: Scaffolding includes a pre-built static HTML wrapper with lightweight runtime error reporting inside the iframe, preventing total preview crashes.

### 7.2 Risk: Google Search API Rate Limits / Exhaustion
- **Mitigation**: Implement query caching layer and exponential backoff retry policy inside the search tool wrapper.

### 7.3 Risk: Long-Running Implementation Agent Step Timeouts
- **Mitigation**: Implementation Agent writes modular single-file or multi-file templates incrementally, sending atomic trace updates over WebSockets so UI displays granular progress.

### 7.4 Risk: Parallel Pipeline Execution Collisions
- **Mitigation**: Enforce single-instance job lock in APScheduler; if a pipeline run is active when the next hour triggers, the scheduler cleanly skips or queues the run.
