# Architecture

## System Design Document

MiLyfe Brain is a local-first AI agent swarm platform built on FastAPI, Next.js 15, Ollama, ChromaDB, and Redis. This document describes the system's internal architecture, execution model, and key design decisions.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 FRONTEND (Next.js 15 + React 19)                │
│                                                                 │
│  Zustand Store ←→ API Client ←→ WebSocket/SSE Event Stream     │
│  9 Panels: Playbook | Dashboard | Chat | Queue | Scheduler     │
│            History | Logs | Settings | Editor                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP REST + WebSocket + SSE
┌────────────────────────────┼────────────────────────────────────┐
│                    BACKEND (FastAPI + Python 3.11)               │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              API Layer (19 Route Modules, 66 Endpoints)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────────────┐  │
│  │ Orchestrator │  │ Agent Swarm │  │    Tool Registry       │  │
│  │  • Parser    │  │ • 9 Roles   │  │  • 18 Built-in Tools  │  │
│  │  • Executor  │  │ • Factory   │  │  • Hook Pipeline       │  │
│  │  • Parallel  │  │ • Msg Bus   │  │  • MCP Protocol        │  │
│  └──────────────┘  └─────────────┘  └───────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌───────────────────────┐  │
│  │    Memory    │  │  Services   │  │       Safety           │  │
│  │ • SQLite     │  │ • Daemon    │  │ • Permission Levels    │  │
│  │ • ChromaDB   │  │ • Scheduler │  │ • Cmd Classifier       │  │
│  │ • Checkpoint │  │ • Queue     │  │ • Approval Flow        │  │
│  └──────────────┘  │ • Skills    │  │ • Audit Logger         │  │
│                     │ • 20+ more  │  └───────────────────────┘  │
│  ┌──────────────┐  └─────────────┘                              │
│  │   Prompts    │  ┌─────────────┐  ┌───────────────────────┐  │
│  │ • Rules      │  │   Plugins   │  │     Hooks / MCP       │  │
│  │ • Styles     │  │ • Loader    │  │ • Pre/Post Pipeline   │  │
│  │ • Slash Cmds │  │ • Manifest  │  │ • MCP Server/Client   │  │
│  └──────────────┘  └─────────────┘  └───────────────────────┘  │
└─────────┬──────────────────┬──────────────────┬─────────────────┘
          │                  │                  │
     ┌────┴─────┐     ┌─────┴──────┐    ┌─────┴──────┐
     │  Ollama  │     │  ChromaDB  │    │   Redis    │
     │  (Host)  │     │  (Docker)  │    │  (Docker)  │
     │  :11434  │     │   :8400    │    │   :6479    │
     └──────────┘     └────────────┘    └────────────┘
```

---

## TAOR Engine

The **Think-Act-Observe-Reflect** (TAOR) engine drives each agent's execution loop:

1. **Think** — Receive task, recall relevant context from ChromaDB, build augmented system prompt
2. **Act** — Call Ollama via httpx, parse response for tool calls (JSON/XML/ReAct formats)
3. **Observe** — Execute tools through the hook pipeline, collect results
4. **Reflect** — Feed results back to LLM, decide if task is complete or needs another cycle (max 3 rounds)

All LLM calls use direct `httpx.AsyncClient` POST to Ollama's `/api/chat` endpoint — no LangChain-Ollama abstraction layer.

---

## 9-Layer Prompt Augmentation

| Layer | Source | Purpose |
|-------|--------|---------|
| 1 | System Identity | Base role definition and personality |
| 2 | `.rules` (system) | Global coding standards and constraints |
| 3 | `.rules` (user) | `~/.milyfe/rules/` user-level overrides |
| 4 | `.rules` (workspace) | `<workspace>/.milyfe/rules/` project rules |
| 5 | Semantic Skills | Auto-activated skill instructions by topic |
| 6 | Output Style | Response formatting (concise, verbose, etc.) |
| 7 | Environment Snapshot | Directory tree, git status, runtime info |
| 8 | Scratchpad | Working memory (todos, decisions, findings) |
| 9 | Vector Recall | Relevant documents from ChromaDB |

Layers are deep-merged with later layers overriding earlier ones.

---

## Agent Lifecycle

```
Spawn (Factory)  →  Initialize (role, model, tools)  →  Assign Task
       │                                                      │
       │                   ┌──────────────────────────────────┘
       │                   ▼
       │            TAOR Loop (max 3 rounds)
       │                   │
       │         ┌─────────┴──────────┐
       │         │ Success            │ Failure
       │         ▼                    ▼
       │    Post to Bus         Debugger Agent
       │    Store Memory        Retry Once
       │         │                    │
       │         └────────┬───────────┘
       │                  ▼
       └────────────── Retire
```

---

## Tool Execution Pipeline

```
Agent requests tool call
        │
        ▼
┌─────────────────┐
│  Parse Tool Call │  Supports: JSON, Markdown, XML, ReAct formats
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Pre-Hooks      │  PathSanitization → FileSizeLimit → AuditLog
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Permission Check│  free | notify | approve | blocked
└────────┬────────┘
         │
         ▼ (if approve → Human-in-the-Loop dialog)
┌─────────────────┐
│  Execute Tool   │  Sandboxed execution with timeout
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Post-Hooks     │  AutoFormat → Truncate → Log Result
└────────┬────────┘
         │
         ▼
   Return to Agent
```

---

## Orchestration Flow

```
User Input (Natural Language / Markdown / JSON)
        │
        ▼
  PlaybookParser (httpx → Ollama)
  Converts NL → structured steps with roles + dependencies
        │
        ▼
  Topological Sort
  Groups independent steps into parallel execution layers
        │
        ▼
  Layer 1: [step_1, step_2]    ← no dependencies (parallel)
  Layer 2: [step_3]            ← depends on step_1 (sequential)
  Layer 3: [step_4, step_5]    ← depends on step_2 (parallel)
        │
        ▼ (per step)
  AgentFactory.spawn(role) → BaseAgent.think() → TAOR loop
        │
        ▼ (on failure)
  Debugger Agent → Analyze → Retry → Mark failed if retry fails
```

---

## Memory Tiers

| Tier | Backend | Scope | Lifetime | Use Case |
|------|---------|-------|----------|----------|
| Scratchpad | In-memory dict | Per-session | Session | Working notes, todos, decisions |
| Context Window | LLM messages | Per-agent | Task | Current conversation history |
| Vector Memory | ChromaDB | Global | Persistent | Semantic recall, document search |
| Structured DB | SQLite | Global | Persistent | Playbooks, logs, skills, settings |
| Workspace Snapshots | Git | Per-playbook | Persistent | Rollback and audit trail |

---

## Safety Layers

| Layer | Mechanism | Scope |
|-------|-----------|-------|
| Input Validation | Pydantic schemas, size limits | API boundary |
| Rate Limiting | 120 req/min per IP | API boundary |
| Path Sandboxing | Restrict to WORKSPACE_DIR | File operations |
| Command Classifier | Allowlist + pattern + injection detection | Shell execution |
| Permission System | free → notify → approve → blocked | All tool calls |
| Human-in-the-Loop | Modal approval dialog via WebSocket | Destructive actions |
| Circuit Breaker | Auto-isolate failing services | External calls |
| Audit Trail | Every action logged with context | All operations |
| Git Snapshots | Auto-commit before/after execution | Workspace changes |

---

## Frontend Architecture

- **Framework:** Next.js 15 (App Router) with React 19
- **State:** Zustand store (agents, events, playbook, approvals, connection status)
- **Styling:** Tailwind CSS 3.4 + Framer Motion animations
- **Icons:** Lucide React
- **Real-time:** WebSocket with auto-reconnect + SSE fallback
- **API Client:** Fully typed TypeScript client covering all 19 endpoint groups

### Component Hierarchy
```
Layout (Sidebar + ThemeProvider)
├── PlaybookInput / PlaybookEditor
├── Dashboard (Progress + TaskGraph + EventLog + Files + Approvals)
├── ChatInterface (hybrid: conversation + tool execution)
├── QueueStatus
├── SchedulerView
├── HistoryView
├── LogViewer
└── SettingsView (models + safety + selftest)
```

---

## Extension Points

| Extension | Mechanism | Location |
|-----------|-----------|----------|
| Custom Agents | Subclass `BaseAgent`, register role | `backend/agents/roles.py` |
| New Tools | Implement tool function, add to registry | `backend/tools/` |
| Plugins | `manifest.json` + `plugin.py`, auto-discovered | `backend/plugins/` |
| MCP Providers | Connect remote tool servers via httpx | `backend/mcp/client.py` |
| Pre/Post Hooks | Subclass hook ABCs, register in pipeline | `backend/hooks/` |
| Custom Skills | YAML with triggers + instructions | `~/.milyfe/skills/` |
| Output Styles | Register new style with prompt template | `backend/prompts/output_styles.py` |
| Slash Commands | Register handler function | `backend/prompts/slash_commands.py` |
| `.rules` Files | YAML config at any directory level | `.milyfe/rules/` |
| Scheduled Jobs | Cron expressions via API | `/api/scheduler/jobs` |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pure httpx for Ollama | Eliminates LangChain-Ollama `KeyError('name')` crash; full control over request/response |
| Pure httpx for ChromaDB | Eliminates `_type` deserialization crash from Python client |
| Single uvicorn worker | Prevents lifespan conflicts with shared SQLite and daemon state |
| Host Ollama (not Docker) | User manages their own models; avoids GPU passthrough complexity |
| Frontend production build | No dev mode in Docker; prevents runtime compilation crashes |
| Resilient startup | Non-critical services wrapped in try/except; app always starts |
| langchain-core only | Kept for `BaseTool` ABC and message types; stable, never touches Ollama |
| SQLite over PostgreSQL | Zero-config, file-based, suitable for single-machine deployment |
| Redis for PubSub | Real-time event fan-out to WebSocket clients; lightweight cache |
| Topic detection before routing | Fast heuristic classification reduces unnecessary LLM calls |
