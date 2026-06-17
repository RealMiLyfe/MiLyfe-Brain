# ADR-0008: Host Ollama (Not Containerized)

## Status
Accepted

## Date
2024-12-01

## Context
Ollama requires direct GPU access (NVIDIA CUDA, AMD ROCm, or Apple Metal) for acceptable inference performance. Containerizing Ollama adds complexity:
- NVIDIA Container Toolkit required for GPU passthrough
- AMD ROCm Docker support is experimental
- Apple Silicon (M1/M2/M3) has no Docker GPU passthrough
- Model storage (4-70GB per model) complicates Docker volumes
- Users need to manage model downloads independently

## Decision
Ollama runs directly on the host machine (not in Docker). The backend container connects to it via `host.docker.internal:11434`. Users install and manage Ollama separately.

## Consequences

### Positive
- Full GPU access without container GPU passthrough complexity
- Works on all platforms (macOS Metal, Linux CUDA/ROCm, Windows)
- Users control their own model library
- Simpler Docker Compose (no GPU device mapping)
- Ollama updates independent of MiLyfe Brain updates

### Negative
- Extra installation step for users (install Ollama separately)
- Must handle Ollama unavailability gracefully (non-fatal health check)
- `host.docker.internal` doesn't work on all Linux configs (needs extra_hosts)
- Can't guarantee model availability at startup

### Neutral
- `docker-compose.gpu.yml` override available for AMD ROCm containerized Ollama
- Backend has model fallback chain for graceful degradation
- Health check reports Ollama status but doesn't block startup

## Alternatives Considered
1. **Ollama in Docker with GPU passthrough** — Platform-specific; breaks on macOS
2. **llama.cpp directly** — Lower level; no model management UI
3. **vLLM in container** — Heavy; requires NVIDIA specifically
4. **Cloud LLM fallback only** — Against local-first mission

## References
- Ollama installation: https://ollama.ai/download
- Docker GPU support: https://docs.docker.com/config/containers/resource_constraints/
