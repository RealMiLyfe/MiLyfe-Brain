# ADR-0007: Frontend Production Build in Docker

## Status
Accepted

## Date
2024-12-01

## Context
Next.js can run in two modes:
- **Development mode** (`next dev`): Hot reload, unoptimized, runtime compilation
- **Production mode** (`next build` + `next start`): Pre-compiled, optimized, static where possible

Running development mode in Docker caused:
- Runtime compilation crashes under memory pressure
- Slow page loads (compiling on first request)
- Unstable HMR over Docker networking
- Excessive memory usage (500MB+ for dev server)

## Decision
Always run the frontend in production mode inside Docker:
1. Multi-stage Dockerfile: build stage compiles, runtime stage serves
2. `npm run build` at image build time
3. `npm run start` (next start) at container runtime
4. No `--reload` or dev mode in any Docker configuration

Development mode is only used locally outside Docker (developers running `npm run dev` on host).

## Consequences

### Positive
- Stable, predictable performance in Docker
- Lower memory footprint (~150MB vs 500MB+)
- Faster page loads (pre-compiled)
- No runtime compilation crashes
- Consistent behavior across environments

### Negative
- Must rebuild Docker image for frontend changes
- No hot reload in Docker (use local dev for that)
- Slightly longer build times

### Neutral
- Frontend development workflow uses host `npm run dev` 
- Docker is for deployment/integration testing only
- CI/CD rebuilds image on every push anyway

## Alternatives Considered
1. **Dev mode in Docker with volume mount** — Unstable; memory issues
2. **Static export (next export)** — Loses SSR capabilities and API routes
3. **Vite instead of Next.js** — Less ecosystem; no SSR out of box

## References
- Next.js deployment documentation
- Docker multi-stage build best practices
