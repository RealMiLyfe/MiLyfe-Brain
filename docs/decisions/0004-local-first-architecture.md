# ADR-0004: Local-First Architecture

## Status
Accepted

## Date
2024-12-01

## Context
MiLyfe Brain is designed as an AI agent orchestration platform. Many similar products require cloud API keys (OpenAI, Anthropic), cloud vector databases (Pinecone), and SaaS services. Our target users want:
- Complete data privacy (no data leaves their machine)
- Zero recurring costs
- No API key management
- Offline capability
- Full control over model selection

## Decision
Design the entire system to run locally with zero external dependencies:
- **LLM**: Ollama on host machine (user manages their own models)
- **Vector DB**: ChromaDB in Docker (self-contained)
- **Database**: SQLite (zero-config, file-based)
- **Cache/PubSub**: Redis in Docker
- **Frontend**: Next.js production build in Docker

One command (`docker compose up`) starts everything except Ollama (which users install separately for GPU access).

## Consequences

### Positive
- Zero cloud costs — completely free to run
- Complete data privacy — nothing leaves the machine
- Works offline (after initial model download)
- No API keys, no sign-ups, no accounts
- User controls model selection and quality
- Simple deployment for non-technical users

### Negative
- Performance limited by user's hardware
- No access to frontier models (GPT-4, Claude) by default
- Larger disk footprint (models are 4-70GB)
- Cannot leverage cloud scale for parallel processing
- Must handle model availability gracefully

### Neutral
- Future cloud provider support planned as optional opt-in (Phase 4)
- Enterprise deployment can still use Kubernetes for scale
- Local-first doesn't preclude cloud — it just doesn't require it

## Alternatives Considered
1. **Cloud-first with local option** — Against core mission; creates dependency
2. **Hybrid mandatory** — Complexity for users who want purely local
3. **WebAssembly LLMs** — Not mature enough; model quality insufficient

## References
- Ollama: https://ollama.ai
- Local-first software principles: https://www.inkandswitch.com/local-first/
