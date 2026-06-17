# ADR-0005: Agent Swarm Pattern

## Status
Accepted

## Date
2024-12-01

## Context
AI agent architectures range from single-agent (one LLM handles everything) to multi-agent (specialized agents collaborate). For complex task execution (planning + research + coding + testing + review), a single agent struggles with:
- Context window limitations
- Role confusion (planner vs executor)
- Quality degradation on diverse subtasks
- No built-in quality checks

## Decision
Implement a 9-agent swarm architecture where each agent has a specialized role, dedicated system prompt, and tool access pattern:

| Role | Responsibility |
|------|---------------|
| Orchestrator | Task decomposition, coordination |
| Researcher | Information gathering, context |
| Coder | Code generation |
| Executor | File operations, shell commands |
| Critic | Code review, quality checks |
| Designer | Architecture, UI/UX decisions |
| Writer | Documentation, reports |
| Debugger | Error diagnosis, fixes |
| Planner | Strategy, planning |

Agents communicate via a message bus (topic-based pub/sub) and are coordinated by the Orchestrator through dependency-aware parallel execution.

## Consequences

### Positive
- Each agent has focused, high-quality prompts
- Parallel execution of independent tasks
- Built-in quality gates (Critic reviews Coder output)
- Clear separation of concerns
- Easier to tune individual agent behavior
- Natural debug/retry flow (Debugger handles failures)

### Negative
- More LLM calls per task (higher total token usage)
- Coordination overhead
- Potential for circular dependencies if poorly orchestrated
- Requires robust inter-agent messaging

### Neutral
- Agent count (9) is fixed but roles are extensible via plugins
- Each agent can use a different model based on task complexity
- Sub-swarm patterns (debate, parallel, sequential) add flexibility

## Alternatives Considered
1. **Single agent with tools** — Simpler but lower quality on complex tasks
2. **Two-agent (planner + executor)** — Too coarse for our use cases
3. **Dynamic agent spawning** — Too complex; fixed roles with dynamic count is sufficient
4. **LangGraph multi-agent** — Considered but we want full control over coordination logic

## References
- AutoGen multi-agent framework concepts
- CrewAI role-based agent design
- Research: "Communicative Agents for Software Development" (ChatDev)
