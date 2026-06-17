# MiLyfe Brain

**100% Free, Local-Only, Open-Source AI Agent Swarm Orchestration Platform**

Describe goals in plain language ("Playbooks"), and a swarm of 9 specialized AI agents collaboratively executes them — planning, researching, coding, executing, reviewing — while you watch in a real-time animated dashboard.

**Zero cloud services. Zero API keys. Zero sign-ups.**

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 15 / React 19 / Tailwind CSS |
| LLM | Ollama (local — Hermes3, Qwen2.5, LLaMA3.1, Phi3) |
| Vector DB | ChromaDB (REST API via httpx) |
| Database | SQLite (async SQLAlchemy) |
| Cache/PubSub | Redis |
| Deployment | Docker Compose |

## Quick Start

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

## 9 Agent Roles

| Role | Name | Purpose |
|------|------|---------|
| Orchestrator | Conductor | Breaks tasks, assigns work, coordinates |
| Researcher | Explorer | Web search, documentation, context |
| Coder | Builder | Writes production code |
| Executor | Runner | File ops, shell commands, deployment |
| Critic | Judge | Code review, quality checks |
| Designer | Architect | UI/UX design, system architecture |
| Writer | Scribe | Documentation, READMEs, reports |
| Debugger | Detective | Error diagnosis, fix suggestions |
| Planner | Strategist | Architecture, planning, decomposition |

## Key Features

- **Playbook System** — Natural language → structured steps → parallel execution
- **18 Agent Tools** — File, shell, code, browser, GUI, search, batch, REPL, scratchpad
- **Real-Time Dashboard** — WebSocket + SSE event streaming
- **Safety System** — 3-tier command classifier, human-in-loop approvals, audit trail
- **Memory** — ChromaDB vector store + SQLite long-term + scratchpad short-term
- **Swarm Patterns** — Parallel, sequential, debate, map-reduce
- **MCP Protocol** — Local server + remote client support
- **Plugin System** — Dynamic discovery and registration
- **Prompt Augmentation** — Hierarchical .rules files, slash commands, 8 output styles
- **Skill Library** — Auto-learn reusable patterns from success

## Strategic Features

- **Onboarding Wizard** — Interactive tutorial, system diagnostics, model recommendations
- **Analytics Dashboard** — Agent performance, success rates, cost equivalency tracking
- **Marketplace** — Community playbooks, skills, and plugins (GitHub-based registry)
- **Voice Interface** — Local STT (Whisper.cpp) + TTS (Piper) — hands-free operation
- **Reproducibility** — Seed locking, run diffing, CI pipeline export (GitHub Actions)
- **Memory Sharing** — Shared agent war room, consensus voting, knowledge graph
- **Compliance** — PII scanning, license detection, data lineage, retention policies
- **Multi-User** — RBAC (admin/user/viewer), shared libraries, approval chains
- **Mobile PWA** — Progressive Web App for status monitoring from any device

## API

19 route modules with 50+ endpoints covering playbooks, agents, chat, streaming, documents, settings, scheduler, queue, notifications, logs, tokens, workspace, self-test, and brain features.

Full OpenAPI docs at `http://localhost:8200/docs`

## Development

```bash
make build          # Build and start all services
make logs           # View logs
make test           # Run backend tests
make health         # Health check
make selftest       # Full E2E self-test
make shell          # Shell into backend
```

## License

MIT
