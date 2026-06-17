# MiLyfe Brain — Architecture Guide

This document explains the system design for developers who want to understand, modify, or extend MiLyfe Brain.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                         │
│  Next.js 15 + React 19 + Zustand + WebSocket/SSE        │
└─────────────────────────┬───────────────────────────────┘
                          │ HTTP / WebSocket
┌─────────────────────────┼───────────────────────────────┐
│                    API LAYER (FastAPI)                    │
│  19 route modules · Middleware · Auth · Rate limiting     │
├─────────────────────────┼───────────────────────────────┤
│                    TAOR ENGINE                            │
│  Think → Act → Observe → Repeat                          │
│  Topic Detection · Prompt Layers · Compaction · Sub-Agents│
├─────────────────────────┼───────────────────────────────┤
│              AGENT SYSTEM        TOOL SYSTEM              │
│  9 Roles · Factory · Bus   18 Tools · Registry · Hooks   │
├─────────────────────────┼───────────────────────────────┤
│           ORCHESTRATION          SERVICES                 │
│  Parser · Executor · Swarm   25+ Background Services      │
├─────────────────────────┼───────────────────────────────┤
│                    PERSISTENCE                            │
│  SQLite (WAL) · ChromaDB (httpx) · Redis (PubSub)        │
└─────────────────────────────────────────────────────────┘
```

---

## Core Execution Flow: TAOR Engine

Every agent interaction goes through the **Think-Act-Observe-Repeat** loop, inspired by modern agent architectures:

```
User Input
    │
    ▼
┌─────────────────┐
│ Topic Detection  │ ← Classify: new_task | follow_up | question | edit | command
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Build Prompt     │ ← 9 Augmentation Layers (see below)
│ (Layered)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ THINK            │ ← Call Ollama /api/chat (pooled httpx)
│ (LLM Reasoning)  │   Circuit breaker + model fallback
└────────┬────────┘
         │
         ▼
┌─────────────────┐    No tool calls?
│ Parse Response   │ ──────────────────→ Return final response
└────────┬────────┘
         │ Has tool calls
         ▼
┌─────────────────┐
│ ACT              │ ← Permission check → Pre-hooks → Execute → Post-hooks
│ (Tool Execution) │   File locking · Parallel when safe · Audit logging
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OBSERVE          │ ← Format results + post-hook reminders
│ (Inject Results) │   Check for sub-agent dispatch signals
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Check    │ ← Compact if >80% of token budget used
└────────┬────────┘
         │
         ▼
    REPEAT (max 10 turns)
```

### Prompt Augmentation Layers (in injection order)

| # | Layer | Source | Purpose |
|---|-------|--------|---------|
| 1 | System Prompt | `roles.py` | Agent identity and behavioral instructions |
| 2 | Output Style | `/output-style` command | Tone/format (concise, verbose, architect...) |
| 3 | Project Rules | `.milyfe/rules/*.yaml` | Coding standards, conventions (CLAUDE.md equiv) |
| 4 | Environment | `env_snapshot` service | Dir tree, git status, runtime info |
| 5 | Memory | ChromaDB + SQLite | Vector recall + learned corrections + failure patterns |
| 6 | Skills | `.milyfe/skills/*.yaml` | Auto-activated domain expertise by keywords |
| 7 | Scratchpad | In-memory per session | Short-term working memory (survives compaction) |
| 8 | Tools | `tool_registry` | Available tool definitions with parameters |
| 9 | Project Intel | `project_intelligence` | Project type, key files, dependency graph |

---

## Agent System

### 9 Specialized Roles

Each role has a distinct system prompt, preferred model tier, and behavioral characteristics:

| Role | Focus | Model Tier |
|------|-------|-----------|
| Orchestrator | Task decomposition, coordination | Heavy |
| Researcher | Information gathering, web search | Light |
| Coder | Production code generation | Heavy |
| Executor | Shell commands, file operations | Heavy |
| Critic | Code review, quality validation | Heavy |
| Designer | Architecture, UI/UX design | Light |
| Writer | Documentation, reports | Light |
| Debugger | Error diagnosis, fix suggestions | Heavy |
| Planner | Strategy, task planning | Light |

### Agent Lifecycle

```
spawn(role, task) → BaseAgent.__init__() → think(task) → [TAOR loop] → retire()
```

- **Factory** manages spawn/retire and enforces `MAX_AGENTS` limit
- **Message Bus** enables inter-agent communication (topic-based pub/sub)
- **Learning Service** tracks corrections, failure patterns, specializations

---

## Tool System

### Execution Pipeline

```
Tool Call (from LLM)
    │
    ▼
Pre-Hooks (PathSanitization, FileSizeLimit, custom)
    │
    ▼
Permission Check (free → notify → approve → blocked)
    │
    ▼
Execute Handler (async function)
    │
    ▼
Post-Hooks (OutputTruncation, AutoFormat, custom)
    │
    ▼
Audit Log (action_type, agent, risk_level, timestamp)
    │
    ▼
Return ToolResult to TAOR engine
```

### Runtime Tool Creation

Agents can create new tools at runtime:
1. Agent writes a Python function
2. Validates syntax with `compile()`
3. Registers with the tool registry
4. Tool becomes available to all agents immediately

---

## Orchestration Engine

### Playbook Execution

```
Natural Language Input
    │
    ▼
PlaybookParser (JSON | Markdown | LLM-based)
    │
    ▼
Topological Sort (group independent steps for parallel execution)
    │
    ▼
Layer-by-Layer Execution:
  Layer 1: [step_1, step_2]  ← parallel (no dependencies)
  Layer 2: [step_3]          ← depends on layer 1
  Layer 3: [step_4, step_5]  ← depends on layer 2
    │
    ▼
On Failure: Debugger Agent → Analyze → Retry Once
    │
    ▼
On Success: Skill Library learns pattern
```

### Enhanced Playbook Engine Features

- **Variables**: `{{step_1.result}}`, `{{env.VAR}}`, `{{input.field}}`
- **Conditionals**: `"{{status}} contains 'error'"` → skip/run step
- **Loops**: `until`, `times`, `foreach` with max iteration caps
- **Composition**: Nested playbooks (playbook within playbook)
- **Dry-Run**: Simulate execution, estimate time/tokens/cost
- **CI Export**: Convert proven playbooks to GitHub Actions or Makefile

---

## Safety Architecture

```
┌──────────────────────────────────────────┐
│          Safety Layers (outer → inner)    │
├──────────────────────────────────────────┤
│ 1. Request Size Limit (10MB)             │
│ 2. Rate Limiting (120/min per IP)        │
│ 3. API Key Auth (optional)               │
│ 4. Path Sandboxing (workspace only)      │
│ 5. Command Classifier (3-tier)           │
│    - Allowlist (fast pass)               │
│    - Pattern matching (regex)            │
│    - Injection detection                 │
│ 6. Permission Levels                     │
│    - free: no check                      │
│    - notify: log prominently             │
│    - approve: human-in-loop              │
│    - blocked: never execute              │
│ 7. Pre-Tool Hooks (sanitize, validate)   │
│ 8. Audit Trail (every action logged)     │
│ 9. Git Snapshots (before/after playbook) │
│ 10. Circuit Breakers (service isolation) │
└──────────────────────────────────────────┘
```

---

## Data Flow

### Memory Tiers

| Tier | Storage | Latency | Use Case |
|------|---------|---------|----------|
| Hot | Redis | <1ms | PubSub, cache, rate limits |
| Warm | SQLite | <10ms | Playbooks, logs, settings, chat history |
| Cold | ChromaDB | <100ms | Vector memory, document search, semantic recall |

### Context Window Management

When context approaches the token limit (default 32K):
1. **Detect** at 80% capacity
2. **Summarize** older messages using the heavy model
3. **Preserve** system prompt + scratchpad + last 4 messages
4. **Inject** summary as a `[Compacted context]` block
5. **Fallback** to rule-based truncation if LLM summarization fails

---

## Frontend Architecture

```
App (page.tsx)
├── Sidebar (navigation between 9 views)
├── Header (notifications, connection status, shortcuts hint)
└── View Router
    ├── PlaybookInput (NL input + templates)
    ├── PlaybookEditor (drag-and-drop step editor)
    ├── Dashboard (progress + task graph + event log + files + approvals)
    ├── Chat (streaming messages + tool execution)
    ├── Queue (running/waiting/completed)
    ├── Scheduler (cron jobs)
    ├── History (past playbook runs)
    ├── Logs (filterable action log)
    └── Settings (models, safety, self-test)
```

### State Management (Zustand)

Single global store with:
- `agents: Map<id, AgentState>` — Active agents
- `events: StreamEvent[]` — Real-time event stream (last 200)
- `currentPlaybook` — Active playbook being viewed
- `pendingApprovals` — Human-in-loop queue
- `notifications` — Notification center
- `isConnected` — WebSocket health

### Real-Time Communication

- **WebSocket** (`/api/stream/ws`) — Bidirectional: events down, commands up (subscribe/filter/approve)
- **SSE** (`/api/stream/sse`) — Unidirectional event stream (fallback)
- **SSE Chat** (`/api/stream/chat`) — Token-by-token streaming responses

---

## Extension Points

| Extension | Location | Method |
|-----------|----------|--------|
| New Tool | `backend/tools/` | Register with `tool_registry` |
| New Agent Role | `backend/agents/roles.py` | Subclass `BaseAgent` |
| New Plugin | `backend/plugins/` | `manifest.json` + `plugin.py` |
| New Skill | `.milyfe/skills/` | YAML with triggers + instructions |
| New Rules | `.milyfe/rules/` | YAML (cascading hierarchy) |
| New Hook | `backend/hooks/` | Implement `PreToolHook` or `PostToolHook` |
| New Swarm Pattern | `backend/graphs/swarm_graph.py` | Subclass `SwarmPattern` |
| New Output Style | `backend/prompts/output_styles.py` | Add to `STYLE_INSTRUCTIONS` |
| New Slash Command | `backend/prompts/slash_commands.py` | `register_command()` |
| New Webhook Trigger | Settings or `.milyfe/triggers.yaml` | Condition + action config |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pure httpx (no langchain-ollama) | Eliminates KeyError('name') crash, full control over requests |
| Pure httpx for ChromaDB | Eliminates '_type' deserialization crash |
| Single uvicorn worker | Shared SQLite + daemon state conflicts with multiple workers |
| SQLite WAL mode | Allows concurrent reads during writes |
| Connection pooling | Shared httpx client prevents connection exhaustion |
| Fire-and-forget post-completion | Memory storage + bus publishing don't block response |
| TAOR engine separation | Clean separation of harness logic from agent intelligence |
| Topological sort for parallelism | Maximize throughput while respecting dependencies |
| 3-tier command classifier | Fast path for safe commands, thorough check for unknowns |
| Circuit breakers per service | Prevent cascade failures when external services go down |

---

## Performance Characteristics

| Operation | Target | Notes |
|-----------|--------|-------|
| Health check | <50ms | No external calls |
| Tool execution (file_read) | <5ms | Direct filesystem |
| Tool execution (shell_exec) | <60s | Configurable timeout |
| LLM call (light model) | 2-10s | Depends on model + hardware |
| LLM call (heavy model) | 5-30s | Depends on model + hardware |
| Playbook parsing | 5-15s | One LLM call for NL→steps |
| Context compaction | 3-10s | One LLM call for summarization |
| WebSocket latency | <10ms | In-process event bus |
| Database query | <10ms | SQLite with WAL + indexes |
| Vector search | 50-200ms | ChromaDB REST API |

---

*For the complete specification, see [FULL_SPEC.md](FULL_SPEC.md).*
