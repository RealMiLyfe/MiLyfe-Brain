# ADR-0009: Circuit Breaker for External Services

## Status
Accepted

## Date
2024-12-01

## Context
MiLyfe Brain depends on three external services (Ollama, ChromaDB, Redis). If any service becomes unresponsive:
- Requests pile up waiting for timeouts
- Thread pool exhaustion cascades to other endpoints
- User experience degrades across the entire application
- Recovery is slow (backlog of queued requests)

## Decision
Implement a circuit breaker pattern for all external service calls:

**States:**
- `CLOSED` (normal) — Requests pass through; failures counted
- `OPEN` (tripped) — Requests immediately fail-fast; no external calls
- `HALF_OPEN` (testing) — Limited requests to test recovery

**Configuration:**
- Failure threshold: 5 consecutive failures → OPEN
- Recovery timeout: 30 seconds → transition to HALF_OPEN
- Success threshold: 2 successes in HALF_OPEN → back to CLOSED

**Applied to:**
- Ollama LLM calls (with model fallback chain)
- ChromaDB vector operations (graceful degradation: skip memory recall)
- Redis cache/pubsub (fall back to in-memory)

## Consequences

### Positive
- Fast failure instead of hanging requests
- Automatic recovery when services come back
- Prevents cascade failures
- Clear health status per service
- Graceful degradation (system works with reduced functionality)

### Negative
- Complexity in circuit breaker state management
- Must define fallback behavior for each service
- Brief window of false-failures during HALF_OPEN testing

### Neutral
- Circuit state exposed via health endpoint
- Prometheus metrics track circuit state transitions
- Future: adaptive thresholds based on historical patterns

## Alternatives Considered
1. **Simple retry with backoff** — Doesn't prevent cascade; still blocks
2. **Bulkhead pattern only** — Isolates but doesn't prevent repeated failures
3. **External service mesh (Istio)** — Overkill for local deployment
4. **No protection** — Unacceptable; one service down breaks everything

## References
- Martin Fowler: Circuit Breaker pattern
- Microsoft: Circuit Breaker pattern (Cloud Design Patterns)
- Python `tenacity` library (used for retry within closed state)
