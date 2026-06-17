# ADR-0010: Kubernetes Deployment Strategy

## Status
Accepted

## Date
2025-01-15

## Context
While MiLyfe Brain is designed as local-first, enterprise customers require:
- High availability (multiple replicas)
- Horizontal scaling
- Rolling deployments with zero downtime
- Environment separation (staging, production)
- Resource limits and auto-scaling
- Centralized logging and monitoring

Docker Compose is insufficient for these requirements.

## Decision
Provide Kubernetes manifests using Kustomize for environment-specific overlays:

**Structure:**
```
k8s/
├── base/              # Shared manifests
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── backend/
│   ├── frontend/
│   ├── chromadb/
│   └── redis/
└── overlays/
    ├── staging/       # Staging-specific patches
    └── production/    # Production-specific patches
```

**Key decisions:**
- Kustomize over Helm (simpler, no templating language)
- Rolling update strategy (maxSurge: 1, maxUnavailable: 0)
- HPA for backend (CPU-based autoscaling)
- PVC for persistent data (SQLite DB, ChromaDB data)
- Ingress with TLS termination
- NetworkPolicy for service isolation

## Consequences

### Positive
- Enterprise-ready deployment
- Zero-downtime rolling updates
- Auto-scaling based on load
- Environment parity (staging mirrors production)
- Resource isolation and limits

### Negative
- Requires Kubernetes cluster (complexity for small teams)
- PVC management for SQLite limits horizontal scaling
- Must handle WebSocket affinity in multi-replica

### Neutral
- PostgreSQL migration (ADR-TBD) will remove PVC constraint for DB
- Ollama remains external (GPU node with DaemonSet possible)
- Docker Compose remains primary for local/dev deployment

## Alternatives Considered
1. **Helm charts** — More flexible but complex templating; Kustomize is simpler
2. **Docker Swarm** — Less ecosystem support; dying platform
3. **Nomad** — Less adoption; fewer managed offerings
4. **ECS/Fargate** — AWS-specific; against multi-cloud goal

## References
- Kustomize documentation: https://kustomize.io
- Kubernetes deployment strategies: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
