# MiLyfe Brain — AI Swarm Build Plan

## Purpose

This document is the execution plan for building out MiLyfe Brain using an AI agent swarm. It defines the exact order of operations, agent assignments, validation gates, and success criteria for each phase.

**Status:** PR5 (`enterprise-complete`) has delivered ~75% of the codebase. This plan focuses on the remaining 25% — fixing critical bugs, wiring integrations, and bringing the system to a runnable state.

---

## Pre-Requisites (Completed in PR5)

| Layer | Status | Files |
|-------|--------|-------|
| Configuration (config.py, .env) | ✅ Done | 2 |
| Data Models (schemas.py) | ✅ Done | 1 |
| Database (database.py, migrations) | ✅ Done | 5 |
| Agent Core (base, roles, factory, bus, parser) | ✅ Done | 5 |
| Tools (registry + 9 tool modules) | ✅ Done (import bugs) | 11 |
| Orchestration (parser, orchestrator, swarm_graph) | ✅ Done | 3 |
| API Routes (19 modules) | ✅ Done | 19 |
| Safety (permissions, approvals, classifier, logger, snapshots) | ✅ Done | 5 |
| Services (25+ modules) | ✅ Done | 25+ |
| Frontend (all components, pages, store) | ✅ Done | 24 |
| Infrastructure (Docker, K8s, CI/CD, Terraform) | ✅ Done | 40+ |
| SDKs (Python, TypeScript, Swift) | ✅ Done | 12 |

---

## Phase 0: CRITICAL BUG FIXES (Agent: Debugger)

**Duration:** 1 session  
**Agent:** DebuggerAgent  
**Gate:** App starts without errors, tool registry populated

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 0.1 | Fix import paths: `from backend.X` → `from X` | tools/__init__.py, tools/file_tools.py, tools/shell_tools.py, tools/search_tools.py, tools/llm_client.py, tools/batch_tools.py | `python -c "from tools import register_all_tools"` succeeds |
| 0.2 | Add `register_all_tools()` to app lifespan | main.py | tool_registry.count() == 18 after startup |
| 0.3 | Wire AgentFactory tool_executor to ToolRegistry | main.py | Agent.think() can execute file_read successfully |
| 0.4 | Fix frontend BASE_URL default port | frontend/src/lib/api.ts | Port 8200 used by default |
| 0.5 | Add telemetry.py stub (prevent crash if enabled) | services/telemetry.py | Import doesn't crash |

### Interface Contract
```python
# After Phase 0, this must work:
from tools import register_all_tools, tool_registry
register_all_tools()
assert tool_registry.count() == 18

from agents.factory import get_agent_factory
factory = get_agent_factory()
factory.set_tool_executor(lambda name, args: tool_registry.execute(name, args))
agent = factory.spawn(role="coder")
result = await agent.think("List files in the workspace")
# result should contain actual file listing (not "tool not available")
```

---

## Phase 1: INTEGRATION WIRING (Agents: Coder + Executor)

**Duration:** 2 sessions  
**Agents:** CoderAgent (implementation), ExecutorAgent (validation)  
**Gate:** End-to-end playbook execution with tools working

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 1.1 | Wire CommandClassifier into shell_exec tool | tools/shell_tools.py, safety/command_classifier.py | `rm -rf /` blocked, `ls` allowed |
| 1.2 | Wire AuditLogger into ToolRegistry post-hook | main.py or tools/__init__.py, safety/logger.py | action_logs table populated after tool execution |
| 1.3 | Wire TokenTracker into BaseAgent._call_llm | agents/base.py, services/token_tracker.py | token_usage table populated after LLM call |
| 1.4 | Wire ApprovalFlow into ToolRegistry for approve-level tools | tools/registry.py, safety/approvals.py, api/routes/streaming.py | file_delete pauses and waits for approval |
| 1.5 | Implement WebSocket/SSE bridge from MessageBus | api/routes/streaming.py | Frontend receives events in real-time |
| 1.6 | Fix Orchestrator per-step DB sessions | graphs/orchestrator.py | Parallel steps don't corrupt shared session |
| 1.7 | Wire ChromaDB vector recall into agent think() | agents/base.py, memory/vector_store.py | Agent context includes relevant past memories |
| 1.8 | Wire SkillLibrary learning on playbook completion | graphs/orchestrator.py, services/skill_library.py | skills table populated after successful playbook |

### Interface Contracts

```python
# 1.1: Command safety
from safety.command_classifier import classify_command
result = classify_command("rm -rf /")
assert result.risk_level == "blocked"

# 1.3: Token tracking
# After agent.think(), token_usage table has new row

# 1.5: WebSocket bridge
# Client connects to /api/stream/ws
# Orchestrator emits "step_started" → client receives it within 1s

# 1.6: Session isolation
# Parallel steps each get own session, commits don't interfere
```

### Dependency Order
```
1.1 (independent)
1.2 (independent)  
1.3 (independent)
1.4 depends on 1.5 (approval needs WebSocket to notify user)
1.5 (independent — highest priority in this phase)
1.6 (independent)
1.7 (independent)
1.8 depends on 1.6 (needs working orchestration)
```

---

## Phase 2: FRONTEND REAL-TIME (Agents: Designer + Coder)

**Duration:** 1-2 sessions  
**Agents:** DesignerAgent (UX logic), CoderAgent (implementation)  
**Gate:** Dashboard shows live events, approval dialog works

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 2.1 | Implement useWebSocket hook | frontend/src/hooks/useWebSocket.ts (new) | Connects to /api/stream/ws, reconnects on drop |
| 2.2 | Wire WebSocket events to Zustand store | frontend/src/lib/store.ts, page.tsx | Store.events updates in real-time |
| 2.3 | Implement ApprovalDialog with WebSocket | frontend/src/components/dashboard/ApprovalDialog.tsx | Shows approval request, sends approve/deny |
| 2.4 | Add event throttling to Dashboard | frontend/src/components/dashboard/Dashboard.tsx | Handles 50+ events/sec without lag |
| 2.5 | Implement PlaybookProgress animated bar | frontend/src/components/dashboard/PlaybookProgress.tsx (new or enhance) | Shows step completion percentage |
| 2.6 | Wire TaskGraph visualization | frontend/src/components/dashboard/TaskGraph.tsx (new or enhance) | Shows dependency graph with live status |

### Interface Contract
```typescript
// useWebSocket hook
const { isConnected, lastEvent, sendMessage } = useWebSocket();
// isConnected reflects actual WS state
// lastEvent updates store automatically
// sendMessage sends approval responses

// Store receives events
store.events // StreamEvent[] — updated by WebSocket
store.pendingApprovals // populated when approve-level tool triggered
```

---

## Phase 3: TEST COVERAGE (Agents: Critic + Coder)

**Duration:** 2 sessions  
**Agents:** CriticAgent (test design), CoderAgent (implementation)  
**Gate:** 70%+ coverage on critical path, all tests pass

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 3.1 | Unit tests: ToolParser (all 5 formats) | tests/test_tool_parser.py | 15+ test cases, 100% parser coverage |
| 3.2 | Unit tests: ToolRegistry (permissions, hooks) | tests/test_registry.py | 10+ tests, permission enforcement verified |
| 3.3 | Unit tests: PlaybookParser (JSON, MD, NL) | tests/test_playbook_parser.py | 12+ tests, all 3 parse paths covered |
| 3.4 | Unit tests: CommandClassifier | tests/test_command_classifier.py | Dangerous commands blocked, safe commands pass |
| 3.5 | Unit tests: AgentFactory lifecycle | tests/test_agent_factory.py | Spawn, think, retire, cleanup_stale |
| 3.6 | Integration test: Full playbook execution | tests/integration/test_playbook_flow.py | Playbook → parse → queue → execute → complete |
| 3.7 | Integration test: API endpoints (CRUD) | tests/integration/test_api.py | All CRUD operations return expected status |
| 3.8 | Frontend: Component render tests | frontend/src/__tests__/ | All 9 views render without crash |

### Test Fixtures Needed
```python
# conftest.py must provide:
- async_client (httpx.AsyncClient with TestClient)
- test_db (in-memory SQLite, auto-migrated)
- mock_ollama (httpx mock returning predictable responses)
- mock_chromadb (httpx mock)
- populated_registry (tool_registry with all tools registered)
```

---

## Phase 4: HARDENING (Agents: Debugger + Critic)

**Duration:** 1-2 sessions  
**Agents:** DebuggerAgent (edge cases), CriticAgent (review)  
**Gate:** No crashes on edge cases, graceful degradation

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 4.1 | Handle Ollama down gracefully (all paths) | agents/base.py, graphs/playbook_parser.py | Clear error message, no crash, playbook marked failed |
| 4.2 | Handle ChromaDB down gracefully | memory/vector_store.py | Agent works without vector recall |
| 4.3 | Handle Redis down gracefully | services/* | Cache miss = proceed without cache |
| 4.4 | Add request validation on all routes | api/routes/*.py | Invalid input returns 422 with details |
| 4.5 | Add timeout to orchestrator step execution | graphs/orchestrator.py | Step fails after agent_timeout seconds |
| 4.6 | Add circuit breaker to LLM calls | agents/base.py, services/circuit_breaker.py | After 3 consecutive failures, short-circuit |
| 4.7 | Graceful shutdown (cancel running tasks) | main.py lifespan | Running playbooks cancelled cleanly on SIGTERM |

---

## Phase 5: DOCKER VALIDATION (Agents: Executor + Debugger)

**Duration:** 1 session  
**Agents:** ExecutorAgent (run commands), DebuggerAgent (fix issues)  
**Gate:** `docker compose up` → health check passes → playbook executes

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 5.1 | Verify Dockerfile builds cleanly | backend/Dockerfile | `docker build ./backend` exits 0 |
| 5.2 | Verify frontend Dockerfile builds | frontend/Dockerfile | `docker build ./frontend` exits 0 |
| 5.3 | Verify docker-compose up (all 4 services) | docker-compose.yml | All services healthy within 60s |
| 5.4 | Test health endpoint through Docker | — | `curl localhost:8200/health` returns 200 |
| 5.5 | Test playbook execution through Docker | — | POST /api/playbooks → status=completed |
| 5.6 | Test frontend connects to backend | — | `curl localhost:3000` renders page |
| 5.7 | Update .env.example with all current vars | .env.example | All settings in config.py have defaults |

---

## Phase 6: DOCUMENTATION & CLEANUP (Agents: Writer + Planner)

**Duration:** 1 session  
**Agents:** WriterAgent (docs), PlannerAgent (roadmap)  
**Gate:** README complete, CHANGELOG written, vision module documented

### Tasks

| # | Task | File(s) | Validation |
|---|------|---------|-----------|
| 6.1 | Write comprehensive README.md | README.md | Covers: what, why, how, quickstart, architecture |
| 6.2 | Write CHANGELOG.md | CHANGELOG.md | Documents all implemented features by version |
| 6.3 | Write CONTRIBUTING.md | CONTRIBUTING.md | Dev setup, coding standards, PR process |
| 6.4 | Document vision features as ROADMAP.md | ROADMAP.md | Clearly marks what's implemented vs planned |
| 6.5 | Clean up dead imports and unused code | backend/**/*.py | No unused imports, no dead code |
| 6.6 | Verify all __init__.py exports are correct | backend/**/__init__.py | Clean public API per module |

---

## Build Execution Summary

| Phase | Sessions | Agent(s) | Key Deliverable |
|-------|----------|----------|-----------------|
| 0 | 1 | Debugger | App starts, tools work |
| 1 | 2 | Coder + Executor | Full integration, end-to-end execution |
| 2 | 1-2 | Designer + Coder | Real-time dashboard |
| 3 | 2 | Critic + Coder | 70%+ test coverage |
| 4 | 1-2 | Debugger + Critic | Edge case handling |
| 5 | 1 | Executor + Debugger | Docker deployment verified |
| 6 | 1 | Writer + Planner | Documentation complete |

**Total: 9-11 sessions to v1.0 shippable state**

---

## Validation Gates (Between Phases)

### Gate 0→1: "App Boots Clean"
```bash
cd backend
python -c "
import asyncio
from main import app
from tools import tool_registry
assert tool_registry.count() == 18
print('GATE 0 PASSED')
"
```

### Gate 1→2: "End-to-End Works"
```bash
# Start services
docker compose up -d

# Create and execute playbook
curl -X POST http://localhost:8200/api/playbooks/ \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","description":"List workspace files","auto_execute":true}'

# Wait 30s, check status
curl http://localhost:8200/api/playbooks/{id}/status
# Expected: status=completed, steps have results
```

### Gate 2→3: "Real-Time Works"
```
1. Open http://localhost:3000
2. Submit a playbook
3. Dashboard shows live agent spawning events
4. Progress bar animates
5. Approval dialog appears for approve-level tools
```

### Gate 3→4: "Tests Pass"
```bash
cd backend
pytest tests/ -v --cov=. --cov-report=term
# Expected: 50+ tests pass, 70%+ coverage on critical files
```

### Gate 5→6: "Production Ready"
```bash
docker compose up -d
# Wait for health
sleep 30
curl -f http://localhost:8200/health
curl -f http://localhost:3000
# Both return 200
```

---

## Decision Log (Append After Each Phase)

| Date | Phase | Decision | Rationale |
|------|-------|----------|-----------|
| — | 0 | Use relative imports throughout | Docker/uvicorn runs from backend/ dir |
| — | 0 | shell_exec stays at "approve" | More secure than spec's "notify" |
| — | 1 | Per-step DB sessions | Prevent asyncio.gather corruption |
| — | — | — | — |

---

## Known Limitations (Documented, Not Fixed)

1. **Single uvicorn worker** — SQLite doesn't support multiple writers
2. **Sequential queue** — One playbook at a time (by design for v1.0)
3. **Host Ollama** — Not containerized, user manages their own models
4. **GPU serialization** — Parallel agents queue at the LLM level
5. **No persistent WebSocket state** — Reconnection loses event history
6. **No user authentication** — Single-user local deployment assumed

---

*End of Build Plan*
