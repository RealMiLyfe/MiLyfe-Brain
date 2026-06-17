# MiLyfe Brain

**AI Agent Swarm Orchestration Platform — 100% Local, Zero Cloud**

MiLyfe Brain is a free, open-source platform that executes complex tasks using a swarm of 9 specialized AI agents. Describe what you want in plain language, and watch agents collaborate in real-time to plan, research, code, execute, and review — all running locally on your hardware.

---

## Key Features

- **9 Specialized Agents** — Orchestrator, Researcher, Coder, Executor, Critic, Designer, Writer, Debugger, Planner
- **Natural Language Playbooks** — Describe tasks in plain English, markdown, or JSON
- **Real-Time Dashboard** — Watch agents think, act, and collaborate with live WebSocket updates
- **18 Built-in Tools** — File ops, shell exec, code sandbox, web browsing, search, REPL, scratchpad
- **Safety First** — Permission tiers (free/notify/approve/blocked), command classifier, human-in-the-loop approvals
- **Vector Memory** — ChromaDB-powered recall so agents learn from past executions
- **Skill Library** — Automatically learns reusable patterns from successful playbooks
- **Circuit Breakers** — Graceful degradation when services are unavailable
- **Zero Dependencies on Cloud** — Runs on Ollama (local LLMs), SQLite, Redis, ChromaDB

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.ai) running on your host machine
- At least one model pulled: `ollama pull phi3:mini`

### Deploy

```bash
# 1. Clone the repository
git clone https://github.com/RealMiLyfe/MiLyfe-Brain.git
cd MiLyfe-Brain

# 2. Create environment file
cp .env.example .env

# 3. Pull recommended models
ollama pull phi3:mini
ollama pull llama3.1:8b

# 4. Start all services
docker compose up -d

# 5. Verify deployment
./scripts/validate_docker.sh
```

### Access

| Service | URL |
|---------|-----|
| Frontend (Dashboard) | http://localhost:3000 |
| Backend API | http://localhost:8200 |
| API Documentation | http://localhost:8200/docs |
| ChromaDB | http://localhost:8400 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 FRONTEND (Next.js 15 + React 19)                │
│  Playbook Input │ Dashboard │ Chat │ Settings │ Real-Time WS    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────────────┐
│               BACKEND (FastAPI + Python 3.11)                   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  19 API      │  │  Orchestrator │  │  9 Agent Roles       │ │
│  │  Routes      │  │  (topo sort)  │  │  (BaseAgent ABC)     │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  18 Tools    │  │  Safety      │  │  Services (25+)      │ │
│  │  + Registry  │  │  + Approvals │  │  Queue, Scheduler... │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────┴────┐     ┌────────┴────┐     ┌────────┴────┐
    │  Ollama │     │  ChromaDB   │     │    Redis    │
    │  (Host) │     │  (Vector)   │     │  (Cache)    │
    └─────────┘     └─────────────┘     └─────────────┘
```

---

## How It Works

1. **You describe a task** — "Build a REST API for managing todos"
2. **PlaybookParser** converts your input into structured steps with agent assignments
3. **Orchestrator** sorts steps by dependencies and executes in parallel layers
4. **Agents** think, call tools, get results, and iterate (max 3 rounds per step)
5. **Dashboard** shows real-time progress via WebSocket events
6. **On completion**, the Skill Library learns the pattern for future use

---

## Agent Roles

| Role | Purpose | Best For |
|------|---------|----------|
| Orchestrator | Coordinates multi-agent workflows | Complex multi-step tasks |
| Researcher | Gathers information and context | Documentation, analysis |
| Coder | Writes production code | Implementation, refactoring |
| Executor | Runs commands and validates | Testing, deployment |
| Critic | Reviews quality and security | Code review, auditing |
| Designer | UI/UX and architecture | Design systems, layouts |
| Writer | Documentation and content | READMEs, guides, reports |
| Debugger | Investigates and fixes bugs | Error diagnosis, patches |
| Planner | Strategy and roadmaps | Architecture, planning |

---

## Tool System

18 tools with permission-based access control:

| Permission | Tools | Behavior |
|-----------|-------|----------|
| **free** | file_read, file_list, glob_search, grep_search, scratchpad_*, repl_* | Execute immediately |
| **notify** | file_write, code_exec, batch_execute, shell_exec (safe commands) | Log prominently |
| **approve** | file_delete, shell_exec (dangerous), web_browse, web_search | Requires user approval via UI |
| **blocked** | — | Never executes |

---

## Development

### Run Tests

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

### Local Development (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8200 --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Makefile Commands

```bash
make up              # Start all services
make down            # Stop all services
make logs            # Tail all logs
make test            # Run test suite
make test-cov        # Run with coverage
make lint            # Run linters
make build           # Rebuild Docker images
make clean           # Full cleanup
make status          # Show container status
```

---

## Configuration

All settings are environment-driven via `.env`. Key options:

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint |
| `DEFAULT_LIGHT_MODEL` | `phi3:mini` | Fast model for parsing |
| `DEFAULT_HEAVY_MODEL` | `llama3.1:8b` | Main reasoning model |
| `MAX_AGENTS` | `10` | Max concurrent agents |
| `AGENT_TIMEOUT` | `300` | Step timeout (seconds) |
| `AUTH_ENABLED` | `false` | API key authentication |
| `REQUIRE_APPROVAL_DESTRUCTIVE` | `true` | Approval for destructive ops |

See `.env.example` for the full list.

---

## Project Structure

```
MiLyfe-Brain/
├── backend/           # FastAPI + Python 3.11
│   ├── agents/        # Agent system (base, roles, factory, bus, parser)
│   ├── api/routes/    # 19 API route modules
│   ├── graphs/        # Orchestration engine
│   ├── memory/        # SQLite + ChromaDB
│   ├── models/        # Pydantic schemas
│   ├── tools/         # 18 tool implementations + registry
│   ├── safety/        # Permissions, approvals, classifier, audit
│   ├── services/      # Background services (queue, scheduler, daemon...)
│   ├── hooks/         # Pre/post tool execution hooks
│   ├── mcp/           # Model Context Protocol
│   ├── prompts/       # Rule loader, slash commands, output styles
│   ├── plugins/       # Dynamic plugin system
│   └── tests/         # 122+ unit tests
├── frontend/          # Next.js 15 + React 19
│   └── src/
│       ├── app/       # App router (single page, 9 views)
│       ├── components/# UI components (dashboard, chat, settings...)
│       ├── hooks/     # WebSocket, playbook status
│       └── lib/       # API client, Zustand store
├── docker-compose.yml # One-command deployment
├── k8s/               # Kubernetes manifests
├── terraform/         # Cloud infrastructure
├── sdks/              # Python, TypeScript, Swift SDKs
├── scripts/           # Utility scripts
└── tests/load/        # Load testing (k6, Locust)
```

---

## Security

- **Path sandboxing** — All file ops restricted to workspace directory
- **Command classification** — Shell commands analyzed for risk before execution
- **Permission tiers** — free → notify → approve → blocked per tool
- **Human-in-the-loop** — Dangerous actions pause and await approval via WebSocket
- **Rate limiting** — 120 requests/minute per IP
- **Circuit breakers** — Auto-isolate failing services
- **Audit trail** — Every tool execution logged with agent context

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and PR guidelines.
