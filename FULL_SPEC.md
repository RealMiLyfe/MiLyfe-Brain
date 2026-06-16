# MiLyfe Brain — Complete Project Specification & Schematics

## Overview

**MiLyfe Brain** is a 100% free, local-only, open-source AI agent swarm orchestration platform. Users describe goals in plain language ("Playbooks"), and a swarm of 9 specialized AI agents collaboratively executes them — planning, researching, coding, executing, reviewing — while the user watches in a real-time animated dashboard.

**Stack:** FastAPI (Python) backend + Next.js 15 / React 19 frontend + Docker Compose  
**LLM:** Ollama (local, any model — Hermes3, Qwen2.5, LLaMA3.1, Phi3)  
**Vector DB:** ChromaDB (REST API via httpx)  
**Database:** SQLite (via SQLAlchemy async)  
**Cache/PubSub:** Redis  
**Zero cloud services. Zero API keys. Zero sign-ups.**

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 15 + React 19)             │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐ ┌───────────────┐ │
│  │ Playbook │ │Dashboard │ │  Chat  │ │ Logs │ │   Settings    │ │
│  │  Input   │ │(Progress)│ │(Hybrid)│ │      │ │(Models/Safety)│ │
│  └──────────┘ └──────────┘ └────────┘ └──────┘ └───────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐ ┌───────────────┐ │
│  │ Playbook │ │  Queue   │ │Schedu- │ │Histo-│ │  Notifica-    │ │
│  │  Editor  │ │  Status  │ │  ler   │ │  ry  │ │    tions      │ │
│  └──────────┘ └──────────┘ └────────┘ └──────┘ └───────────────┘ │
│                                                                     │
│              WebSocket + SSE Real-Time Event Stream                  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │ HTTP + WebSocket
┌─────────────────────────┼───────────────────────────────────────────┐
│                   BACKEND (FastAPI + Python 3.11)                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    API LAYER (19 Routes)                     │   │
│  │  playbooks | agents | chat | tasks | streaming | health     │   │
│  │  settings | documents | selftest | workspace | download     │   │
│  │  notifications | logs | scheduler | tokens | queue          │   │
│  │  filesystem | daemon | export_import                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐   │
│  │   ORCHESTRATOR   │  │   AGENT SWARM    │  │   TOOL SYSTEM  │   │
│  │  (graphs/)       │  │   (agents/)      │  │   (tools/)     │   │
│  │                  │  │                  │  │                │   │
│  │ • Playbook Parse │  │ • BaseAgent ABC  │  │ • file_tools   │   │
│  │ • Step Executor  │  │ • 9 Roles        │  │ • shell_tools  │   │
│  │ • Parallel Exec  │  │ • Factory        │  │ • code_tools   │   │
│  │ • Retry+Debug    │  │ • Message Bus    │  │ • browser      │   │
│  │ • Swarm Patterns │  │ • Tool Parser    │  │ • gui_tools    │   │
│  └──────────────────┘  └──────────────────┘  │ • search       │   │
│                                               │ • batch        │   │
│  ┌──────────────────┐  ┌──────────────────┐  │ • repl         │   │
│  │    MEMORY        │  │   SERVICES       │  │ • scratchpad   │   │
│  │  (memory/)       │  │  (services/)     │  │ • registry     │   │
│  │                  │  │                  │  └────────────────┘   │
│  │ • SQLite (async) │  │ • Daemon         │                       │
│  │ • ChromaDB REST  │  │ • Scheduler      │  ┌────────────────┐   │
│  │ • Checkpointer   │  │ • Queue Manager  │  │    SAFETY      │   │
│  └──────────────────┘  │ • Token Tracker  │  │  (safety/)     │   │
│                         │ • Notifications  │  │                │   │
│  ┌──────────────────┐  │ • Skill Library  │  │ • Permissions  │   │
│  │   PROMPTS        │  │ • Memory Persist │  │ • Approvals    │   │
│  │  (prompts/)      │  │ • Daily Digest   │  │ • Cmd Classif. │   │
│  │                  │  │ • Env Snapshot   │  │ • Audit Logger │   │
│  │ • Rule Loader    │  │ • Topic Detect   │  │ • Git Snapshot │   │
│  │ • Slash Commands │  │ • Session Branch │  └────────────────┘   │
│  │ • Output Styles  │  │ • Sub-Agent Iso  │                       │
│  └──────────────────┘  │ • Semantic Skills│  ┌────────────────┐   │
│                         │ • Quality Comp.  │  │  MCP / HOOKS   │   │
│  ┌──────────────────┐  │ • Config Hier.   │  │                │   │
│  │   PLUGINS        │  │ • Model Fallback │  │ • MCP Server   │   │
│  │  (plugins/)      │  │ • Circuit Break  │  │ • MCP Client   │   │
│  │                  │  │ • Output Valid.  │  │ • Pre/Post Hook│   │
│  │ • Loader         │  │ • Workspace Git  │  │ • Hook Registry│   │
│  │ • Manifest JSON  │  │ • Workspace Iso  │  └────────────────┘   │
│  │ • Dynamic Reg.   │  │ • Runtime Set.   │                       │
│  └──────────────────┘  │ • Logging Config │                       │
│                         └──────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
              │                    │                    │
    ┌─────────┼────────┐  ┌───────┼────────┐  ┌───────┼────────┐
    │   Ollama (Host)  │  │   ChromaDB     │  │     Redis      │
    │   Port 11434     │  │   Port 8400    │  │   Port 6479    │
    │                  │  │                │  │                │
    │ hermes3:latest   │  │ Vector memory  │  │ Cache + PubSub │
    │ qwen2.5:14b      │  │ REST API       │  │                │
    │ llama3.1:8b      │  │ (httpx calls)  │  │                │
    │ phi3:mini        │  │                │  │                │
    └──────────────────┘  └────────────────┘  └────────────────┘
```

---


## File Structure (Complete)

```
MiLyfe-Brain/
├── docker-compose.yml              # One-command deployment
├── docker-compose.gpu.yml          # Optional AMD ROCm GPU override
├── .env.example                    # Environment configuration template
├── .pre-commit-config.yaml         # Ruff, eslint, security hooks
├── Makefile                        # Dev commands (make up, make logs, etc.)
├── LICENSE                         # MIT
├── README.md                       # Project landing page
│
├── backend/                        # FastAPI + Python 3.11
│   ├── Dockerfile                  # python:3.11-slim, playwright, uvicorn
│   ├── requirements.txt            # All Python dependencies
│   ├── pyproject.toml              # Ruff/pytest/mypy config
│   ├── main.py                     # App entry: middleware, lifespan, routes
│   ├── config.py                   # Pydantic Settings (env-driven)
│   │
│   ├── agents/                     # AI Agent System
│   │   ├── __init__.py
│   │   ├── base.py                 # BaseAgent ABC (think/act loop, httpx→Ollama)
│   │   ├── roles.py               # 9 specialized agent implementations
│   │   ├── factory.py             # AgentFactory (spawn, track, retire)
│   │   ├── message_bus.py         # Inter-agent topic-based messaging
│   │   └── tool_parser.py         # Parse tool calls from LLM output
│   │
│   ├── api/
│   │   ├── __init__.py            # OpenAPI tag metadata
│   │   └── routes/                # 19 API route modules
│   │       ├── playbooks.py       # CRUD + execute playbooks
│   │       ├── agents.py          # Spawn/list/retire agents
│   │       ├── chat.py            # Hybrid chat (pure httpx, tool loop)
│   │       ├── tasks.py           # Task management
│   │       ├── streaming.py       # WebSocket + SSE events
│   │       ├── health.py          # Health check endpoint
│   │       ├── settings_api.py    # Runtime settings CRUD
│   │       ├── documents.py       # PDF/file upload + ChromaDB storage
│   │       ├── selftest.py        # E2E self-test (ollama, chromadb, tools)
│   │       ├── workspace.py       # File tree, read, recent files
│   │       ├── download.py        # Zip workspace output
│   │       ├── notifications.py   # Notification center
│   │       ├── logs.py            # Action log search/filter/export
│   │       ├── scheduler.py       # Cron job management
│   │       ├── tokens.py          # Token usage stats
│   │       ├── queue.py           # Playbook execution queue
│   │       ├── filesystem.py      # Local filesystem browser
│   │       ├── daemon.py          # Autonomous daemon control
│   │       └── export_import.py   # Playbook JSON backup/restore
│   │
│   ├── graphs/                    # Orchestration Engine
│   │   ├── orchestrator.py        # Step executor (parallel, retry, debug)
│   │   ├── playbook_parser.py     # NL/MD/JSON → structured steps (httpx)
│   │   └── swarm_graph.py         # Sub-swarm patterns (parallel/seq/debate)
│   │
│   ├── memory/                    # Persistence Layer
│   │   ├── database.py            # SQLite: tables, init, migrations
│   │   ├── vector_store.py        # ChromaDB REST API (pure httpx)
│   │   └── checkpointer.py       # LangGraph state checkpointing
│   │
│   ├── models/
│   │   └── schemas.py             # Pydantic models (all API types)
│   │
│   ├── tools/                     # Agent Tool Implementations
│   │   ├── registry.py            # Central tool registry
│   │   ├── file_tools.py          # read, write, delete, list
│   │   ├── shell_tools.py         # Shell execution (sandboxed)
│   │   ├── code_tools.py          # Sandboxed Python execution
│   │   ├── browser_tools.py       # Playwright web automation
│   │   ├── gui_tools.py           # PyAutoGUI desktop automation
│   │   ├── llm_client.py          # Direct Ollama client utility
│   │   ├── search_tools.py        # Glob + Grep (first-class search)
│   │   ├── batch_tools.py         # Parallel multi-tool execution
│   │   ├── repl_tools.py          # Persistent REPL sessions
│   │   └── scratchpad_tools.py    # Working memory tools
│   │
│   ├── safety/                    # Security & Permissions
│   │   ├── permissions.py         # Permission levels per action type
│   │   ├── approvals.py           # Human-in-the-loop approval flow
│   │   ├── command_classifier.py  # Semantic risk classification
│   │   ├── logger.py              # Audit trail logger
│   │   └── snapshots.py           # Git-based workspace snapshots
│   │
│   ├── prompts/                   # Prompt Augmentation System
│   │   ├── rule_loader.py         # Hierarchical .rules file merging
│   │   ├── slash_commands.py      # /review, /explain, /fix, etc.
│   │   └── output_styles.py       # concise, verbose, architect, etc.
│   │
│   ├── hooks/                     # Tool Middleware Pipeline
│   │   ├── base.py                # PreToolHook / PostToolHook ABCs
│   │   └── registry.py            # Hook execution engine
│   │
│   ├── mcp/                       # Model Context Protocol
│   │   ├── schema.py              # MCPToolSchema, MCPToolCall, MCPToolResult
│   │   ├── server.py              # Local MCP server (tool registry)
│   │   └── client.py              # Remote MCP provider client
│   │
│   ├── services/                  # Background Services
│   │   ├── daemon.py              # Autonomous file watcher + processor
│   │   ├── daily_digest.py        # Morning summary generation
│   │   ├── skill_library.py       # Learn reusable patterns from success
│   │   ├── memory_persistence.py  # Long-term memory (SQLite)
│   │   ├── model_fallback.py      # Fallback chain (httpx, no langchain)
│   │   ├── workspace_git.py       # Auto git snapshots
│   │   ├── workspace_isolator.py  # Per-playbook workspace isolation
│   │   ├── output_validator.py    # Validate generated code/files
│   │   ├── notification_service.py# WebSocket push notifications
│   │   ├── queue_manager.py       # Sequential playbook execution
│   │   ├── scheduler_service.py   # Cron-based scheduled execution
│   │   ├── token_tracker.py       # Token/cost tracking
│   │   ├── runtime_settings.py    # DB-backed runtime config
│   │   ├── context_manager.py     # Context window management
│   │   ├── circuit_breaker.py     # Circuit breaker for external services
│   │   ├── logging_config.py      # Rotating file log handler
│   │   ├── topic_detector.py      # Input classification/routing
│   │   ├── session_branching.py   # Git-like conversation forking
│   │   ├── subagent_isolation.py  # Isolated sub-agent execution
│   │   ├── semantic_skills.py     # Auto-activated skill injection
│   │   ├── quality_compaction.py  # Heavy-model context compaction
│   │   ├── config_hierarchy.py    # Multi-layer config cascade
│   │   └── env_snapshot.py        # Project environment capture
│   │
│   ├── plugins/                   # Plugin System
│   │   ├── loader.py              # Dynamic plugin discovery + loading
│   │   └── example-weather/       # Example plugin
│   │       ├── manifest.json
│   │       └── plugin.py
│   │
│   └── tests/
│       ├── conftest.py            # Pytest fixtures
│       └── test_security.py       # 20 security tests
│
├── frontend/                      # Next.js 15 + React 19
│   ├── Dockerfile                 # node:20-alpine, production build
│   ├── .dockerignore              # Exclude node_modules, .next
│   ├── package.json               # Dependencies
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.ts
│   └── src/
│       ├── app/
│       │   ├── layout.tsx         # Root layout + ErrorBoundary
│       │   └── page.tsx           # Main page (9-panel router)
│       ├── lib/
│       │   ├── api.ts             # Full API client (all endpoints)
│       │   └── store.ts           # Zustand global state
│       ├── hooks/
│       │   └── usePlaybookStatus.ts  # Polling hook
│       └── components/
│           ├── ErrorBoundary.tsx
│           ├── layout/
│           │   └── Sidebar.tsx         # 9-item navigation
│           ├── playbook/
│           │   ├── PlaybookInput.tsx   # Main input + templates
│           │   ├── PlaybookEditor.tsx  # Step editor
│           │   └── ExportImport.tsx    # JSON backup/restore
│           ├── dashboard/
│           │   ├── Dashboard.tsx       # Main dashboard
│           │   ├── PlaybookProgress.tsx# Animated progress bar
│           │   ├── TaskGraph.tsx       # Task visualization
│           │   ├── EventLog.tsx        # Live event stream
│           │   ├── WorkspaceFiles.tsx  # Agent-created files
│           │   ├── ApprovalDialog.tsx  # Human-in-loop dialog
│           │   ├── DownloadButton.tsx  # Zip download
│           │   └── ErrorRetryPanel.tsx # Error display + retry
│           ├── chat/
│           │   └── ChatInterface.tsx   # Hybrid chat (tools, GitHub)
│           ├── agents/
│           │   └── AgentAvatar.tsx     # Animated agent icons
│           ├── history/
│           │   └── HistoryView.tsx     # Past playbook runs
│           ├── logs/
│           │   └── LogViewer.tsx       # Search/filter/export logs
│           ├── notifications/
│           │   └── NotificationBell.tsx# Unread badge + dropdown
│           ├── queue/
│           │   └── QueueStatus.tsx     # Running/waiting/history
│           ├── scheduler/
│           │   └── SchedulerView.tsx   # Cron job management
│           ├── settings/
│           │   └── SettingsView.tsx    # Models, safety, self-test
│           └── theme/
│               ├── ThemeProvider.tsx
│               └── ThemeToggle.tsx
│
├── examples/                      # Example playbooks
│   └── organize-photos.json
│
└── scripts/
    └── backup.sh                  # Automated backup script
```

---


## Agent Roles (9)

| Role | Name | Purpose | Preferred Model |
|------|------|---------|-----------------|
| `orchestrator` | Conductor | Breaks tasks, assigns work, coordinates | hermes3:latest |
| `researcher` | Explorer | Web search, documentation, context gathering | llama3.1:8b |
| `coder` | Builder | Writes production code | qwen2.5:14b |
| `executor` | Runner | File ops, shell commands, deployment | qwen2.5:14b |
| `critic` | Judge | Code review, quality checks, testing | qwen2.5:14b |
| `designer` | Architect | UI/UX design, system architecture | hermes3:latest |
| `writer` | Scribe | Documentation, READMEs, reports | hermes3:latest |
| `debugger` | Detective | Error diagnosis, fix suggestions | qwen2.5:14b |
| `planner` | Strategist | Architecture, planning, task decomposition | hermes3:latest |

---

## Agent Execution Loop (BaseAgent.think())

```
1. Receive task description
2. Recall relevant documents from ChromaDB (if available)
3. Build system prompt (role + rules + skills + style + env snapshot)
4. Call Ollama /api/chat via httpx
5. Parse response for tool calls (JSON, markdown, XML, ReAct formats)
6. If tool calls found:
   a. Run pre-hooks (sanitize, validate, audit)
   b. Execute tool
   c. Run post-hooks (format, log, truncate)
   d. Feed result back to LLM
   e. Repeat (max 3 rounds)
7. If no tool calls: return final response
8. Store result in vector memory for future recall
9. Post to message bus for other agents
```

---

## Orchestration Flow

```
User Input (Natural Language / Markdown / JSON)
        │
        ▼
┌─────────────────────┐
│  PlaybookParser     │  Converts NL → structured steps
│  (httpx → Ollama)   │  Supports: plain text, markdown, JSON
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Orchestrator       │  Topological sort by dependencies
│                     │  Groups independent steps for parallel execution
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  Execution Layers (parallel within each)    │
│                                             │
│  Layer 1: [step_1, step_2]  ←── no deps    │
│  Layer 2: [step_3]          ←── depends 1  │
│  Layer 3: [step_4, step_5]  ←── depends 2  │
└─────────┬───────────────────────────────────┘
          │
          ▼ (for each step)
┌─────────────────────┐
│  AgentFactory.spawn │  Create agent for step's role
│  → BaseAgent.think()│  Execute with tool access
└─────────┬───────────┘
          │
          ▼ (on failure)
┌─────────────────────┐
│  Debugger Agent     │  Analyze error, suggest fix
│  → Retry once       │  If retry fails → mark failed
└─────────────────────┘
```

---

## API Endpoints (19 Route Modules)

### Playbooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/playbooks/` | Create + execute a playbook |
| GET | `/api/playbooks/` | List all playbooks |
| GET | `/api/playbooks/{id}` | Get playbook details |
| GET | `/api/playbooks/{id}/status` | Real-time execution status |
| GET | `/api/playbooks/{id}/graph` | Task graph for visualization |
| POST | `/api/playbooks/{id}/rerun` | Re-execute a playbook |
| DELETE | `/api/playbooks/{id}` | Delete a playbook |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/agents/roles` | List available agent roles |
| GET | `/api/agents/active` | List currently active agents |
| POST | `/api/agents/spawn` | Spawn a new agent |
| POST | `/api/agents/{id}/message` | Send message to agent |
| DELETE | `/api/agents/{id}` | Retire an agent |

### Chat (Hybrid — tools + conversation)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/send` | Send message (with tool execution) |
| GET | `/api/chat/history/{session_id}` | Get chat history |
| GET | `/api/chat/sessions` | List chat sessions |
| DELETE | `/api/chat/sessions/{id}` | Delete a session |
| POST | `/api/chat/intervene/{playbook_id}` | Intervene in running playbook |
| GET | `/api/chat/capabilities` | List chat agent capabilities |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload PDF/TXT/MD → ChromaDB |
| POST | `/api/documents/search` | Semantic search documents |
| GET | `/api/documents/` | List uploaded documents |
| DELETE | `/api/documents/{id}` | Delete a document |

### Streaming
| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/api/stream/ws` | WebSocket real-time events |
| GET | `/api/stream/sse` | SSE event stream |

### Queue / Scheduler / Tokens / Logs / Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/queue/status` | Queue state (running/waiting) |
| GET | `/api/scheduler/jobs` | List scheduled jobs |
| POST | `/api/scheduler/jobs` | Create scheduled job |
| GET | `/api/tokens/stats` | Token usage statistics |
| GET | `/api/logs/` | Search/filter action logs |
| GET | `/api/notifications/` | Get notifications |
| POST | `/api/notifications/read-all` | Mark all read |

### Other
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/selftest/run` | Full E2E self-test |
| GET | `/api/workspace/tree` | Workspace directory tree |
| GET | `/api/download/workspace` | Zip workspace output |
| POST | `/api/settings/` | Save runtime settings |
| GET | `/api/settings/` | Load runtime settings |
| POST | `/api/playbooks/io/export/{id}` | Export playbook JSON |
| POST | `/api/playbooks/io/import` | Import playbook JSON |
| GET | `/api/brain/daemon/status` | Daemon status |
| GET | `/api/brain/skills` | List learned skills |
| GET | `/api/brain/memory` | Agent memories |
| GET | `/api/brain/digest` | Daily digest |

---


## Data Models (Pydantic Schemas)

```python
# Enums
AgentRole: orchestrator | researcher | coder | executor | critic | designer | writer | debugger | planner
TaskStatus: pending | running | awaiting_approval | completed | failed | cancelled
TaskComplexity: light | medium | heavy
ActionType: file_read | file_write | file_delete | shell_exec | browse_web | gui_action | code_exec | llm_call | memory_store | memory_recall

# Core Models
PlaybookStep:
  id: str
  description: str
  agent_role: Optional[AgentRole]
  depends_on: List[str]
  complexity: TaskComplexity
  tools_needed: List[str]

PlaybookCreate:
  title: str (max 500)
  description: str (max 50000)
  raw_text: Optional[str] (max 100000)
  steps: Optional[List[PlaybookStep]] (max 50)
  auto_execute: bool

AgentState:
  id, role, name, status, current_task, thoughts, actions_taken, progress, model, avatar_color

StreamEvent:
  event_type: str (agent_spawned | thought | action | progress | error | completed)
  agent_id, agent_role, data: Dict, timestamp

ApprovalRequest:
  id, action_type, description, details, agent_id, agent_role, risk_level

GraphNode:
  id, label, type, status, position: {x, y}, data

GraphEdge:
  id, source, target, label, animated
```

---

## Database Schema (SQLite)

```sql
-- Playbooks
playbooks (id, title, description, raw_text, status, created_at, completed_at, error)

-- Steps
playbook_steps (id, playbook_id, description, agent_role, status, result, started_at, completed_at)

-- Action Logs (audit trail)
action_logs (id, playbook_id, agent_id, agent_role, action_type, description, result, timestamp)

-- Chat Messages
chat_messages (id, session_id, role, content, model, tokens_used, tool_calls, attachments, created_at)

-- Agent Memories (long-term)
agent_memories (id, role, memory_type, content, importance, recall_count, created_at)

-- Skills (learned patterns)
skills (id, name, description, category, steps_json, source_playbook_id, success_count, created_at)

-- Settings (runtime config)
settings (key, value, updated_at)

-- Scheduled Jobs
scheduled_jobs (id, playbook_id, title, cron_expression, enabled, last_run, next_run)

-- Notifications
notifications (id, title, message, type, read, created_at)

-- Token Usage
token_usage (id, agent_id, agent_role, model, playbook_id, prompt_tokens, completion_tokens, timestamp)
```

---

## Tool Registry

| Tool Name | Category | Description | Permission |
|-----------|----------|-------------|------------|
| `file_read` | File | Read file contents | free |
| `file_write` | File | Write/create files | notify |
| `file_delete` | File | Delete files | approve |
| `file_list` | File | List directory contents | free |
| `shell_exec` | Shell | Execute shell commands | notify |
| `code_exec` | Code | Sandboxed Python execution | notify |
| `web_browse` | Browser | Playwright page interaction | approve |
| `web_search` | Browser | Web search | notify |
| `gui_action` | GUI | PyAutoGUI desktop control | approve |
| `glob_search` | Search | Find files by path pattern | free |
| `grep_search` | Search | Regex content search | free |
| `batch_execute` | Batch | Multiple tools in parallel | notify |
| `repl_execute` | REPL | Persistent Python session | notify |
| `repl_inspect` | REPL | Inspect REPL variable | free |
| `repl_variables` | REPL | List REPL variables | free |
| `scratchpad_write` | Memory | Write to working memory | free |
| `scratchpad_read` | Memory | Read working memory | free |
| `scratchpad_update` | Memory | Update scratchpad entry | free |

Permission levels: `free` (no check) → `notify` (log prominently) → `approve` (human approval required) → `blocked` (never execute)

---

## 16 Architectural Features

### 1. Layered Prompt Augmentation
- `.rules` YAML files cascade: system → `~/.milyfe/rules/` → `<workspace>/.milyfe/rules/` → `<subdir>/.milyfe/rules/`
- Deep merge (later overrides earlier)
- Injects coding standards, identity, tone, custom rules into every prompt

### 2. Pre/Post Tool Hooks
- Pipeline of deterministic middleware on every tool call
- PreToolHook: can modify params, block execution
- PostToolHook: can transform output, add metadata
- Built-in: PathSanitization, FileSizeLimit, AuditLog, AutoFormat

### 3. Topic Detection
- Classifies input: new_task, follow_up, question, edit, command, feedback, clarification
- Fast heuristic (regex/keyword) handles 80%+
- Determines if context should reset or continue

### 4. Session Branching
- checkpoint(messages) → save state
- fork(checkpoint_id) → new branch from that point
- switch_branch(branch_id) → change active branch
- merge_branch(source, target) → combine results

### 5. Scratchpad (Short-Term Memory)
- Per-session structured working memory
- Categories: todo, note, decision, finding, blocker
- Survives context compaction (re-injected after summarization)
- Available as agent tools: scratchpad_write/read/update

### 6. Environment Snapshot
- Captures at session start: directory tree, git status, recent files, runtime info
- Injected into agent prompts for situational awareness
- Auto-refreshes on significant workspace changes

### 7. Batch Tool Execution
- Single agent requests multiple independent tools in one turn
- All execute in parallel (asyncio.gather)
- Results returned together — reduces LLM round-trips
- Max 10 parallel calls per batch

### 8. Fast Search Primitives
- `glob_search`: fuzzy path matching (e.g., `**/*.py`, `src/**/test_*.ts`)
- `grep_search`: regex content search with context lines
- Skips: .git, node_modules, __pycache__, .next, venv

### 9. Command Safety Classifier
- 3-tier: allowlist (fast pass) → pattern matching → injection detection
- Risk levels: safe, caution, dangerous, blocked
- Detects: piping to shell, backtick execution, variable expansion, command chaining

### 10. MCP (Model Context Protocol)
- MCPToolSchema: structured tool definition with parameters
- MCPServer: register tools with handlers, validate params, invoke
- MCPClient: connect to remote MCP providers (httpx)
- Enables microservice tool architecture

### 11. Sub-Agent Context Isolation
- Sub-agents run in their own message history
- Only the FINAL result returns to the parent
- All intermediate reasoning/failures/dead-ends discarded
- Prevents context pollution

### 12. Semantic Skill Activation
- Skills have trigger keywords in YAML frontmatter
- Auto-activate when input matches triggers (threshold: 0.3 relevance)
- Instructions injected into context automatically
- Built-in: api_design, error_handling, testing, security, docker
- Custom skills: `~/.milyfe/skills/` or `<workspace>/.milyfe/skills/`

### 13. Quality Compaction
- Uses the HEAVY model (same tier, not light) for summarization
- Structured output: decisions, files, state, next steps, blockers, key context
- Replaces entire prior conversation (not just old messages)
- Falls back to rule-based if LLM fails

### 14. Configuration Hierarchy
- 4 layers: system defaults → `~/.milyfe/config.yaml` → `<workspace>/.milyfe/config.yaml` → subdirectory
- Dot-notation access: `config.get("models.heavy")`
- Covers: models, safety, behavior, output, workspace settings

### 15. Output Styles
- 8 built-in: default, concise, verbose, architect, pair_programmer, diff_only, junior_friendly
- Switch mid-session via API
- Appends style instructions to system prompt
- Custom style registration supported

### 16. REPL Execution
- Persistent Python sessions — variables survive between calls
- Incremental solution building (no re-executing everything each time)
- Tools: repl_execute, repl_inspect, repl_variables
- Separate from one-shot code_exec (which is sandboxed + stateless)

---


## Frontend Architecture

### Tech Stack
- Next.js 15 (App Router, production build)
- React 19
- TypeScript 5.6
- Tailwind CSS 3.4
- Framer Motion (animations)
- Zustand (state management)
- Lucide React (icons)

### Pages / Views (9)
1. **Playbook** — Natural language input + 6 quick-start templates + document upload + model selection
2. **Editor** — Step-by-step playbook editor (add/remove/reorder steps, assign agent roles)
3. **Dashboard** — Live execution: progress bar, task graph, event log, workspace files, download
4. **Chat** — Hybrid conversational interface with tool execution, GitHub integration, file context
5. **Queue** — Running/waiting/completed playbook queue
6. **Scheduler** — Cron job management with presets (@hourly, @daily, custom)
7. **History** — Past playbook runs with replay
8. **Logs** — Searchable action log (filter by role/type/playbook), pagination, export
9. **Settings** — Model selection, safety toggles, self-test runner, document memory

### State Management (Zustand)
```typescript
BrainStore {
  agents: Map<string, AgentState>     // Active agents
  events: StreamEvent[]                // Real-time event stream
  currentPlaybook: Playbook | null     // Active playbook
  pendingApprovals: ApprovalRequest[]  // Human-in-loop queue
  isConnected: boolean                 // WebSocket status
}
```

### API Client (api.ts)
Full typed client covering all 19 endpoint groups: playbookApi, agentApi, chatApi, settingsApi, documentsApi, workspaceApi, selfTestApi, notificationsApi, queueApi, schedulerApi, exportImportApi, tokensApi, logsApi, downloadApi + WebSocketClient with auto-reconnect.

---

## Docker Compose Services

| Service | Image | Port (host) | Port (internal) | Volume |
|---------|-------|-------------|-----------------|--------|
| chromadb | chromadb/chroma:latest | 8400 | 8000 | chroma_data |
| redis | redis:7-alpine | 6479 | 6379 | redis_data |
| backend | ./backend (Dockerfile) | 8200 | 8200 | workspace_data, db_data |
| frontend | ./frontend (Dockerfile) | 3000 | 3000 | — |

**Host Ollama** (not containerized): Port 11434. Backend connects via `host.docker.internal`.

---

## Configuration (.env)

```
CHROMA_PORT=8400
REDIS_PORT=6479
BACKEND_PORT=8200
FRONTEND_PORT=3000
OLLAMA_BASE_URL=http://host.docker.internal:11434
DEFAULT_LIGHT_MODEL=phi3:mini
DEFAULT_HEAVY_MODEL=llama3.1:8b
PREMIUM_MODEL=llama3.1:70b
MAX_AGENTS=10
REQUIRE_APPROVAL_DESTRUCTIVE=true
REQUIRE_APPROVAL_BROWSING=true
REQUIRE_APPROVAL_GUI=true
AUTO_GIT_SNAPSHOTS=true
CONTEXT_SUMMARIZE_THRESHOLD=32000
MAX_RETRIES=3
AGENT_TIMEOUT=300
AUTH_ENABLED=false
API_KEY=change-me-to-a-real-secret
CORS_ALLOW_ALL=true
DATABASE_URL=sqlite:////data/milyfe.db
WORKSPACE_DIR=/workspace
```

---

## Dependencies (requirements.txt)

**Core:** fastapi, uvicorn, pydantic, pydantic-settings, python-multipart  
**LLM:** langchain-core (BaseTool interface only), langgraph  
**Vector:** chromadb (telemetry fix only — actual API calls use httpx)  
**Database:** sqlalchemy, aiosqlite, alembic  
**Cache:** redis  
**Web Automation:** playwright  
**GUI:** pyautogui, pillow, opencv-python-headless  
**Sandbox:** restrictedpython  
**PDF:** PyPDF2  
**WebSocket:** websockets, sse-starlette  
**HTTP:** httpx (ALL LLM calls, ALL ChromaDB calls)  
**Utilities:** structlog, tenacity, gitpython, jinja2, pyyaml, orjson, python-dotenv, setuptools, soundfile

**Frontend:** next, react, react-dom, framer-motion, lucide-react, zustand, tailwindcss, clsx, tailwind-merge, class-variance-authority, sonner

---

## Middleware Stack (main.py)

1. **RequestSizeLimitMiddleware** — 10MB max request body
2. **RateLimitMiddleware** — 120 requests/minute per IP
3. **APIKeyAuthMiddleware** — Optional API key enforcement
4. **CORSMiddleware** — Configurable origins

---

## Startup Sequence (Lifespan)

1. Validate environment variables
2. Initialize SQLite database (create tables, run migrations)
3. Start queue processor (background task)
4. Start scheduler service
5. Start autonomous daemon (file watcher) — wrapped in try/except
6. Initialize workspace git — wrapped in try/except
7. Wire notification service to WebSocket — wrapped in try/except
8. Health check Ollama connection (non-fatal if unavailable)
9. ChromaDB telemetry monkey-patch (prevents PostHog crash)

---

## Security Model

- **Path sandboxing:** All file ops restricted to WORKSPACE_DIR + ~/brain
- **Shell safety:** Command classifier (allowlist + pattern + injection detection)
- **Rate limiting:** 120 req/min per IP
- **Request size:** 10MB max
- **Auth:** Optional API key (for network-exposed deployments)
- **CORS:** Configurable (restrictive by default in production)
- **Permission levels:** free → notify → approve → blocked per action type
- **Circuit breaker:** Automatic failure isolation for chromadb/redis/ollama
- **Audit trail:** Every tool execution logged with agent/role/playbook context
- **Git snapshots:** Automatic workspace backup before/after playbook execution

---

## Key Design Decisions

1. **Pure httpx for LLM calls** — No langchain-ollama. Direct POST to Ollama /api/chat. Eliminates KeyError('name') crash.
2. **Pure httpx for ChromaDB** — No chromadb Python client for vector ops. Direct REST API calls. Eliminates '_type' deserialization crash.
3. **Single uvicorn worker** — Multiple workers cause lifespan conflicts with shared SQLite and daemon state.
4. **Frontend production build** — `npm run build` + `npm run start`. No dev mode in Docker (prevents runtime compile crashes).
5. **Host Ollama** — Not containerized. User manages their own models. Backend connects via host.docker.internal.
6. **Resilient startup** — Non-critical services (daemon, git, notifications) wrapped in try/except. App always starts.
7. **langchain-core only** — Kept for BaseTool ABC and message types. Stable, never touches Ollama directly.

---

## Deployment

```bash
# Prerequisites: Docker, Docker Compose, Ollama running on host
ollama pull phi3:mini
ollama pull llama3.1:8b

# Deploy
cp .env.example .env
docker compose up --build -d

# Access
# Frontend: http://localhost:3000
# Backend API: http://localhost:8200
# API Docs: http://localhost:8200/docs
```

---

*End of specification.*
