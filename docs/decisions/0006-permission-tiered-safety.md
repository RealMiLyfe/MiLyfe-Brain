# ADR-0006: Tiered Permission Safety System

## Status
Accepted

## Date
2024-12-01

## Context
AI agents executing arbitrary tools (file write, shell exec, web browse) present significant safety risks. Without guardrails, an agent could:
- Delete critical system files
- Execute malicious shell commands
- Browse inappropriate content
- Exfiltrate data via network calls
- Modify system configuration

We need a permission system that balances safety with usability — agents should be able to work autonomously on safe operations while requiring human oversight for dangerous ones.

## Decision
Implement a 4-tier permission system applied per action type:

| Level | Behavior | Example Actions |
|-------|----------|----------------|
| `free` | Execute immediately, minimal logging | file_read, file_list, grep |
| `notify` | Execute immediately, prominent audit log | file_write, shell_exec, code_exec |
| `approve` | Block until human approves via UI | file_delete, web_browse, gui_action |
| `blocked` | Never execute, hard reject | (reserved for dangerous patterns) |

Additionally:
- Command classifier analyzes shell commands for risk (injection, piping, expansion)
- Path sandboxing restricts all file ops to WORKSPACE_DIR
- Audit trail logs every tool execution with full context
- Git snapshots before/after destructive operations

## Consequences

### Positive
- Users maintain control over dangerous operations
- Safe operations proceed without friction
- Full audit trail for accountability
- Configurable per-deployment (enterprise can lock down more)
- Semantic risk classification catches novel threats

### Negative
- Approval flow blocks execution (latency for approve-level actions)
- Command classifier may have false positives
- Users must be present for approve-level operations

### Neutral
- Permission levels are configurable via settings API
- Enterprise deployments can customize thresholds
- Future: ML-based risk scoring could reduce false positives

## Alternatives Considered
1. **All actions require approval** — Too slow; kills autonomous capability
2. **No safety system** — Unacceptable risk for file/shell operations
3. **Allowlist only** — Too restrictive; can't anticipate all safe commands
4. **Sandbox VM per agent** — Heavy resource cost; complex orchestration

## References
- OWASP guidelines for AI agent security
- Principle of least privilege (PoLP)
