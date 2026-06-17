# MiLyfe Brain

**100% Free, Local-Only AI Agent Swarm Platform**

MiLyfe Brain is an open-source AI agent swarm orchestration platform that runs entirely on your hardware. Describe goals in plain language ("Playbooks"), and a swarm of 9 specialized AI agents collaboratively executes them — planning, researching, coding, executing, and reviewing — while you watch in a real-time animated dashboard. Zero cloud services. Zero API keys. Zero sign-ups.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 15 / React 19 / Tailwind CSS |
| LLM | Ollama (local — Hermes3, Qwen2.5, LLaMA3.1, Phi3) |
| Vector DB | ChromaDB (REST API via httpx) |
| Database | SQLite (async via SQLAlchemy) |
| Cache/PubSub | Redis |

---

## Quick Start

```bash
# Prerequisites: Docker, Docker Compose, Ollama running on host
ollama pull phi3:mini && ollama pull llama3.1:8b

# Clone and launch
git clone https://github.com/YOUR_USERNAME/MiLyfe-Brain.git
cd MiLyfe-Brain
cp .env.example .env
docker compose up --build -d
```

| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8200 |
| API Documentation | http://localhost:8200/docs |
| ChromaDB | http://localhost:8400 |

---

## Agent Roles

| # | Role | Name | Purpose |
|---|------|------|---------|
| 1 | `orchestrator` | Conductor | Breaks tasks, assigns work, coordinates the swarm |
| 2 | `researcher` | Explorer | Web search, documentation, context gathering |
| 3 | `coder` | Builder | Writes production code |
| 4 | `executor` | Runner | File ops, shell commands, deployment |
| 5 | `critic` | Judge | Code review, quality checks, testing |
| 6 | `designer` | Architect | UI/UX design, system architecture |
| 7 | `writer` | Scribe | Documentation, READMEs, reports |
| 8 | `debugger` | Detective | Error diagnosis, fix suggestions |
| 9 | `planner` | Strategist | Architecture, planning, task decomposition |

---

## Features

### Agent Swarm
- 9 specialized AI agents with distinct roles and personalities
- Inter-agent message bus for collaboration
- Agent lifecycle management (spawn, track, retire)
- Parallel and sequential swarm execution patterns
- Sub-agent context isolation
- Automatic debugger agent on failure with retry

### Orchestration
- Natural language → structured playbook parsing
- Topological dependency sorting with parallel execution
- Playbook queue with sequential processing
- Cron-based scheduled execution
- Session branching (checkpoint, fork, merge)
- Dry-run mode for preview

### Tools & Execution
- 18 built-in tools (file, shell, code, browser, GUI, search, REPL, batch)
- Pre/Post tool hook middleware pipeline
- Batch parallel tool execution (up to 10 concurrent)
- Persistent REPL sessions with variable survival
- Sandboxed Python code execution
- Playwright web automation & PyAutoGUI desktop control

### Memory & Knowledge
- ChromaDB vector memory for semantic recall
- SQLite long-term structured storage
- Scratchpad short-term working memory
- Learned skills library from successful runs
- Document upload (PDF/TXT/MD) with vector indexing
- Daily digest generation

### Safety & Security
- 4-tier permission system (free → notify → approve → blocked)
- Human-in-the-loop approval dialogs
- Command safety classifier (allowlist + pattern + injection detection)
- Path sandboxing to workspace directory
- Rate limiting (120 req/min)
- Audit trail logging for every action
- Git workspace snapshots before/after execution
- Circuit breaker for external service failures

### Frontend Dashboard
- Real-time WebSocket + SSE event streaming
- Animated task graph visualization
- 9-panel navigation (Playbook, Editor, Dashboard, Chat, Queue, Scheduler, History, Logs, Settings)
- Dark/light theme with Framer Motion animations
- Notification center with unread badges
- Workspace file browser with zip download

### Configuration & Extensibility
- Plugin system with manifest-based discovery
- MCP (Model Context Protocol) server and client
- Hierarchical `.rules` YAML configuration cascade
- Semantic skill auto-activation
- 8 output styles (concise, verbose, architect, pair_programmer, etc.)
- Slash commands (/review, /explain, /fix)
- Topic detection for intelligent routing

---

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│            FRONTEND (Next.js 15 + React 19)               │
│   Playbook | Dashboard | Chat | Queue | Settings | Logs   │
└─────────────────────────┬─────────────────────────────────┘
                          │ HTTP + WebSocket + SSE
┌─────────────────────────┼─────────────────────────────────┐
│              BACKEND (FastAPI + Python 3.11)               │
│                                                           │
│  ┌─────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │ Orchestrator│  │ Agent Swarm│  │   Tool Registry   │  │
│  │  (graphs/)  │  │ (agents/)  │  │    (tools/)       │  │
│  └─────────────┘  └────────────┘  └───────────────────┘  │
│  ┌─────────────┐  ┌────────────┐  ┌───────────────────┐  │
│  │   Memory    │  │  Services  │  │  Safety / Hooks   │  │
│  │ (memory/)   │  │(services/) │  │ (safety/ hooks/)  │  │
│  └─────────────┘  └────────────┘  └───────────────────┘  │
└───────┬──────────────────┬──────────────────┬─────────────┘
        │                  │                  │
   ┌────┴────┐      ┌─────┴─────┐     ┌─────┴─────┐
   │ Ollama  │      │ ChromaDB  │     │   Redis   │
   │ :11434  │      │  :8400    │     │   :6479   │
   └─────────┘      └───────────┘     └───────────┘
```

---

## API

66 REST endpoints across 19 route modules. Full interactive documentation at `/docs` when running.

Key endpoint groups: `playbooks`, `agents`, `chat`, `tasks`, `streaming`, `documents`, `queue`, `scheduler`, `tokens`, `logs`, `notifications`, `settings`, `workspace`, `selftest`, `daemon`, `export_import`, `download`, `filesystem`, `health`.

---

## Development

```bash
make build          # Build all containers
make up             # Start services (detached)
make logs           # Tail all logs
make test           # Run pytest with coverage
make lint           # Run ruff linter
make format         # Auto-format with ruff
make health         # Check all service health
make selftest       # Run E2E self-tests
make clean          # Remove containers + volumes
make shell          # Shell into backend container
make status         # Show container status
```

---

## CLI

```bash
milyfe run "Build a REST API for a todo app"   # Run a task
milyfe run --file playbook.json                # Run from file
milyfe run --dry-run "Refactor auth module"    # Preview without executing
milyfe chat "Explain this error"               # Chat with agent
milyfe chat --stream "Write a haiku"           # Stream response tokens
milyfe status                                  # System health overview
milyfe list                                    # List playbooks
milyfe health                                  # Health check
milyfe selftest                                # Run connectivity tests
milyfe models                                  # List available models
milyfe logs --limit 50                         # Recent action logs
milyfe daemon start|stop|status                # Control background daemon
```

---

## Project Structure

```
MiLyfe-Brain/
├── docker-compose.yml          # One-command deployment
├── .env.example                # Environment template
├── Makefile                    # Dev commands
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic settings
│   ├── cli.py                  # CLI entry point
│   ├── agents/                 # Agent swarm (base, roles, factory, bus)
│   ├── api/routes/             # 19 API route modules
│   ├── graphs/                 # Orchestration engine
│   ├── memory/                 # SQLite + ChromaDB + checkpointer
│   ├── tools/                  # 18 tool implementations
│   ├── safety/                 # Permissions, approvals, classifier
│   ├── prompts/                # Rule loader, slash commands, styles
│   ├── services/               # 20+ background services
│   ├── plugins/                # Plugin system + examples
│   ├── hooks/                  # Pre/post tool middleware
│   └── mcp/                    # Model Context Protocol
├── frontend/
│   └── src/
│       ├── app/                # Next.js app router
│       ├── components/         # React components (9 panels)
│       ├── lib/                # API client + Zustand store
│       └── hooks/              # Custom React hooks
├── examples/                   # Example playbooks
└── scripts/                    # Utility scripts
```

---

## License

[MIT](LICENSE) — Use it, fork it, ship it.
