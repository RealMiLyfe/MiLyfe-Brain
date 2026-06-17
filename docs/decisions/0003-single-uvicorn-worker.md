# ADR-0003: Single Uvicorn Worker

## Status
Accepted

## Date
2024-12-01

## Context
Standard FastAPI deployment guidance suggests running multiple uvicorn workers (via gunicorn or uvicorn --workers N) for production. However, MiLyfe Brain uses:
- SQLite as the primary database (file-based, limited concurrent write support)
- In-memory state for daemon, scheduler, and agent tracking
- Background tasks that maintain singleton state (queue processor, file watcher)

Multiple workers would create multiple independent instances, each with their own:
- SQLite connections (write conflicts)
- Agent registries (lost state)
- Daemon instances (duplicate file watching)
- WebSocket connection pools (fragmented)

## Decision
Run a single uvicorn worker process. Scale horizontally via Kubernetes replicas with proper session affinity when needed, rather than intra-process workers.

## Consequences

### Positive
- No SQLite write conflicts
- Singleton services work correctly (daemon, scheduler, queue)
- WebSocket connections stay consistent
- Simpler deployment and debugging
- All agent state in one process

### Negative
- Limited to single-core CPU utilization per container
- Must scale horizontally (multiple pods) for high load
- Requires sticky sessions for WebSocket in multi-pod setup

### Neutral
- asyncio provides concurrency within the single worker
- I/O-bound workloads (LLM calls, ChromaDB queries) benefit from async regardless
- Future PostgreSQL migration (ADR-TBD) will remove the SQLite constraint

## Alternatives Considered
1. **Multiple workers + Redis for shared state** — Significant refactor; premature for local-first product
2. **Multiple workers + PostgreSQL** — Planned for Phase 3 (enterprise scale)
3. **Gunicorn preload** — Doesn't solve in-memory state sharing

## References
- Uvicorn deployment docs: https://www.uvicorn.org/deployment/
- SQLite concurrency: https://www.sqlite.org/wal.html
