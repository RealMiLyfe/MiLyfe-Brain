# ADR-0001: Pure httpx for LLM Calls

## Status
Accepted

## Date
2024-12-01

## Context
The initial prototype used `langchain-ollama` to communicate with the Ollama API. This caused recurring `KeyError('name')` crashes due to response format mismatches between langchain-ollama versions and Ollama API versions. The abstraction layer added complexity without providing meaningful value for our use case (direct local LLM calls).

## Decision
Replace all `langchain-ollama` usage with direct HTTP calls via `httpx` to the Ollama `/api/chat` and `/api/generate` endpoints. Retain `langchain-core` only for the `BaseTool` ABC and message type definitions (stable, well-tested interfaces).

## Consequences

### Positive
- Eliminates the `KeyError('name')` crash entirely
- Full control over request/response handling
- Easier to implement streaming (SSE from Ollama)
- No dependency version conflicts between langchain-ollama and Ollama server
- Simpler debugging — raw HTTP requests/responses
- Supports any Ollama model without adapter updates

### Negative
- Must manually handle retry logic (mitigated by `tenacity`)
- Must manually implement token counting from response metadata
- No automatic prompt formatting (we handle this in BaseAgent)

### Neutral
- `langchain-core` remains for BaseTool interface compatibility
- Future multi-provider support will need per-provider httpx adapters

## Alternatives Considered
1. **Pin langchain-ollama version** — Fragile; breaks on Ollama server updates
2. **Use litellm** — Adds another dependency; still an abstraction layer
3. **Use ollama-python SDK** — Less mature; limited async support at the time

## References
- Ollama API documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
- httpx documentation: https://www.python-httpx.org/
