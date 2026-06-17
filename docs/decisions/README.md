# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for MiLyfe Brain.

## What is an ADR?

An ADR captures an important architectural decision made along with its context and consequences. They serve as historical documentation of why certain decisions were made.

## Format

Each ADR follows this template:
- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Date**: When the decision was made
- **Context**: What is the issue that we're seeing that motivates this decision?
- **Decision**: What is the change we're proposing?
- **Consequences**: What becomes easier or harder as a result?
- **Alternatives Considered**: What other options were evaluated?

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [0001](0001-pure-httpx-for-llm-calls.md) | Pure httpx for LLM Calls | Accepted | 2024-12-01 |
| [0002](0002-pure-httpx-for-chromadb.md) | Pure httpx for ChromaDB | Accepted | 2024-12-01 |
| [0003](0003-single-uvicorn-worker.md) | Single Uvicorn Worker | Accepted | 2024-12-01 |
| [0004](0004-local-first-architecture.md) | Local-First Architecture | Accepted | 2024-12-01 |
| [0005](0005-agent-swarm-pattern.md) | Agent Swarm Pattern | Accepted | 2024-12-01 |
| [0006](0006-permission-tiered-safety.md) | Tiered Permission Safety System | Accepted | 2024-12-01 |
| [0007](0007-frontend-production-build.md) | Frontend Production Build in Docker | Accepted | 2024-12-01 |
| [0008](0008-host-ollama-not-containerized.md) | Host Ollama (Not Containerized) | Accepted | 2024-12-01 |
| [0009](0009-circuit-breaker-pattern.md) | Circuit Breaker for External Services | Accepted | 2024-12-01 |
| [0010](0010-kubernetes-deployment-strategy.md) | Kubernetes Deployment Strategy | Accepted | 2025-01-15 |

## Creating a New ADR

1. Copy the template from any existing ADR
2. Number sequentially (next: 0011)
3. Use kebab-case filename: `NNNN-short-title.md`
4. Add to the index table above
5. Submit via PR with the relevant code changes
