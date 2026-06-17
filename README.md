# MiLyfe Brain

**100% free, local-only, open-source AI agent swarm orchestration platform.**

Users describe goals in plain language ("Playbooks"), and a swarm of 9 specialized AI agents collaboratively executes them — planning, researching, coding, executing, reviewing — while you watch in a real-time animated dashboard.

Zero cloud services. Zero API keys. Zero sign-ups.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 15 / React 19 |
| LLM | Ollama (local — Hermes3, Qwen2.5, LLaMA3.1, Phi3) |
| Vector DB | ChromaDB (REST API via httpx) |
| Database | SQLite (SQLAlchemy async) |
| Cache/PubSub | Redis |
| Deployment | Docker Compose |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Ollama](https://ollama.ai/) running on your host machine

### Deploy

```bash
# Pull models
ollama pull phi3:mini
ollama pull llama3.1:8b

# Clone and deploy
git clone https://github.com/RealMiLyfe/MiLyfe-Brain.git
cd MiLyfe-Brain
cp .env.example .env
docker compose up --build -d
```

### Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8200 |
| API Docs (Swagger) | http://localhost:8200/docs |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              FRONTEND (Next.js 15 + React 19)                │
│  Playbook Input │ Dashboard │ Chat │ Logs │ Settings         │
│              WebSocket + SSE Real-Time Event Stream           │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP + WebSocket
┌──────────────────────────┼───────────────────────────────────┐
│              BACKEND (FastAPI + Python 3.11)                  │
│  19 API Routes │ Orchestrator │ Agent Swarm │ Tools          │
│  Memory (SQLite + ChromaDB) │ Safety │ Plugins │ MCP         │
└──────────┬───────────────────┬───────────────────┬───────────┘
           │                   │                   │
   ┌───────┴──────┐   ┌───────┴──────┐   ┌───────┴──────┐
   │ Ollama (Host)│   │   ChromaDB   │   │    Redis     │
   │  Port 11434  │   │  Port 8400   │   │  Port 6479   │
   └──────────────┘   └──────────────┘   └──────────────┘
```

---

## Agent Roles (9)

| Role | Name | Purpose |
|------|------|---------|
| `orchestrator` | Conductor | Breaks tasks, assigns work, coordinates |
| `researcher` | Explorer | Web search, documentation, context gathering |
| `coder` | Builder | Writes production code |
| `executor` | Runner | File ops, shell commands, deployment |
| `critic` | Judge | Code review, quality checks, testing |
| `designer` | Architect | UI/UX design, system architecture |
| `writer` | Scribe | Documentation, READMEs, reports |
| `debugger` | Detective | Error diagnosis, fix suggestions |
| `planner` | Strategist | Architecture, planning, task decomposition |

---

## Features

- **Natural Language Playbooks** — Describe what you want; the swarm figures out how
- **Real-Time Dashboard** — Watch agents think, act, and collaborate live
- **9 Specialized Agents** — Each with unique tools and expertise
- **Hybrid Chat** — Conversational AI with tool execution built in
- **Human-in-the-Loop** — Approval dialogs for destructive/sensitive actions
- **18 Built-in Tools** — File ops, shell, code sandbox, browser, GUI, search, REPL
- **Parallel Execution** — Independent steps run simultaneously
- **Retry + Debug** — Failed steps auto-retry with debugger agent analysis
- **Memory** — Long-term vector memory (ChromaDB) + SQLite persistence
- **Scheduling** — Cron-based automated playbook execution
- **Plugin System** — Extend with custom tools via manifest.json
- **MCP Protocol** — Model Context Protocol for microservice tool architecture
- **Git Snapshots** — Automatic workspace backup before/after execution
- **Circuit Breakers** — Graceful degradation when services are down
- **Rate Limiting** — 120 req/min per IP, 10MB max request size
- **Dark Theme** — Beautiful animated UI with Framer Motion

---

## Development

```bash
# Start services
make up

# View logs
make logs

# Run tests
make test

# Run self-test (checks ollama, chromadb, redis, tools)
make selftest

# Lint
make lint

# Stop
make down

# Full cleanup
make clean
```

---

## Configuration

Copy `.env.example` to `.env` and customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API endpoint |
| `DEFAULT_LIGHT_MODEL` | `phi3:mini` | Fast model for simple tasks |
| `DEFAULT_HEAVY_MODEL` | `llama3.1:8b` | Quality model for complex tasks |
| `MAX_AGENTS` | `10` | Max concurrent agents |
| `REQUIRE_APPROVAL_DESTRUCTIVE` | `true` | Approve file deletions |
| `AUTH_ENABLED` | `false` | Enable API key auth |
| `AUTO_GIT_SNAPSHOTS` | `true` | Auto git backup |

---

## API Overview

19 route modules providing complete REST API coverage:

- **Playbooks** — CRUD + execute + status + graph + rerun
- **Agents** — Spawn, list, message, retire
- **Chat** — Hybrid conversational AI with tools
- **Tasks** — Task management and control
- **Streaming** — WebSocket + SSE real-time events
- **Documents** — Upload PDF/TXT + semantic search (ChromaDB)
- **Queue** — Execution queue management
- **Scheduler** — Cron job management
- **Tokens** — Usage statistics
- **Logs** — Searchable action logs with export
- **Notifications** — Push notification center
- **Settings** — Runtime configuration
- **Workspace** — File tree browsing
- **Download** — Zip workspace output
- **Self-Test** — E2E health verification
- **Filesystem** — Local filesystem browser
- **Daemon** — Autonomous file watcher
- **Export/Import** — Playbook JSON backup/restore
- **Health** — Service health check

---

## Security

- Path sandboxing (all file ops restricted to workspace)
- Shell command classifier (allowlist + pattern + injection detection)
- Rate limiting (120 req/min per IP)
- Request size limit (10MB)
- Optional API key auth
- Permission levels: free → notify → approve → blocked
- Audit trail (every tool execution logged)
- Git snapshots (automatic workspace backup)

---

## License

MIT — see [LICENSE](LICENSE)
