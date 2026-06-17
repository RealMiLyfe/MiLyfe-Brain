# Changelog

All notable changes to MiLyfe Brain are documented in this file.

## [2.0.0] — 2026-06-17

### Added

#### Core Platform
- 9 specialized AI agent roles with detailed system prompts
- BaseAgent ABC with think/act loop (httpx → Ollama, max 3 tool rounds)
- AgentFactory with lifecycle management (spawn, track, retire, cleanup)
- Inter-agent MessageBus with topic-based pub/sub and message history
- ToolParser supporting 5 formats: JSON blocks, XML, ReAct, inline JSON, arrays

#### Orchestration
- PlaybookParser: NL/Markdown/JSON → structured steps with role inference
- Orchestrator: topological sort, parallel layers, per-step DB sessions
- Queue Manager: sequential FIFO playbook execution
- Scheduler Service: cron-based recurring playbook execution
- Skill Library: auto-learns reusable patterns from successful playbooks

#### Tool System
- 18 built-in tools with central registry and permission enforcement
- Pre/post hook pipeline for tool middleware
- File tools (read, write, delete, list) with path sandboxing
- Shell tools with command safety classifier integration
- Code execution (RestrictedPython sandbox)
- Search tools (glob, grep)
- Batch execution (parallel tool calls)
- REPL sessions (persistent Python)
- Scratchpad (working memory)

#### Safety & Security
- 4-tier permission system: free → notify → approve → blocked
- Human-in-the-loop approval flow with asyncio.Event + WebSocket
- Command classifier: allowlist + pattern matching + injection detection
- Audit logger: every tool execution recorded to database
- Path sandboxing with symlink resolution
- Rate limiting (120 req/min/IP)
- Request size limits (10MB)

#### Frontend
- Next.js 15 + React 19 + TypeScript + Tailwind CSS
- 9 navigation views: Playbook, Editor, Dashboard, Chat, Queue, Scheduler, History, Logs, Settings
- Real-time WebSocket integration with auto-reconnect
- ApprovalDialog: floating modal for approve/deny actions
- TaskGraph: vertical pipeline visualization with status colors
- PlaybookProgress: animated progress bar with shimmer effect
- Zustand state management with typed store
- Framer Motion animations throughout
- Dark/light theme toggle

#### Infrastructure
- Docker Compose: 4 services (backend, frontend, ChromaDB, Redis)
- Multi-stage Dockerfiles (slim Python, Alpine Node)
- Kubernetes manifests (base + staging/production overlays)
- Terraform modules (compute, networking, database, AI services, observability)
- CI/CD: GitHub Actions (lint, test, build, deploy)
- Security scanning workflow
- SDKs: Python, TypeScript, Swift clients

#### Resilience
- Circuit breakers for Ollama, ChromaDB, Redis
- Graceful degradation when services unavailable
- Step-level timeouts in orchestrator
- Graceful shutdown (queue stop, daemon stop, agent retirement)
- Health endpoint with circuit breaker status

#### Memory & Persistence
- SQLite async (aiosqlite) with 11 ORM models
- ChromaDB vector store (pure httpx REST, circuit breaker protected)
- Alembic migrations (4 versions)
- Token usage tracking per agent/model/playbook
- Long-term agent memories

#### Monitoring
- Structured logging with configurable levels
- Prometheus metrics endpoint (optional)
- OpenTelemetry instrumentation (optional)
- Sentry integration (optional)
- Health check with service connectivity status

### Fixed
- Import path inconsistency in tools/ module (from backend.X → from X)
- Tool registry not populated on startup
- Agent factory not wired to tool registry
- Frontend API URL pointing to wrong port
- Orchestrator sharing DB sessions across parallel steps
- docker-compose using server-side URL for client-side env var

### Security
- Shell exec elevated to "approve" permission (stricter than spec)
- Fork bomb detection in command classifier
- Command injection detection (backticks, $(), pipe-to-shell)
- Path traversal prevention with .resolve() + .relative_to()

---

## [1.0.0] — 2026-06-15

### Added
- Initial project structure and specification
- Enterprise infrastructure (K8s, Terraform, CI/CD)
- Vision module scaffolding (experimental features)

---

*Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).*
