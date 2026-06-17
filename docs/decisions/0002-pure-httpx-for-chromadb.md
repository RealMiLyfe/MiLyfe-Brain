# ADR-0002: Pure httpx for ChromaDB

## Status
Accepted

## Date
2024-12-01

## Context
The ChromaDB Python client (`chromadb`) has a heavy dependency tree and causes `_type` deserialization crashes when the client version doesn't exactly match the server version. ChromaDB exposes a full REST API that covers all operations we need (create collection, add documents, query by embedding/text).

## Decision
Use `httpx` to call ChromaDB's REST API directly instead of using the `chromadb` Python client for vector operations. The `chromadb` package is only imported for telemetry monkey-patching (disabling PostHog analytics that causes startup crashes in Docker).

## Consequences

### Positive
- Eliminates `_type` deserialization crashes
- Reduces dependency footprint significantly
- Full control over retry behavior and error handling
- Version-independent — works with any ChromaDB server version that supports REST API v1
- Easier to swap ChromaDB for another vector DB in the future (just change HTTP calls)

### Negative
- Must manually construct embedding requests
- Must handle pagination for large result sets
- No automatic collection type validation

### Neutral
- ChromaDB's REST API is stable and well-documented
- We still use ChromaDB's Docker image as the server

## Alternatives Considered
1. **Pin chromadb client version** — Breaks when server updates in Docker
2. **Use Qdrant instead** — More operational complexity; ChromaDB is simpler for local-first
3. **Use pgvector** — Would require PostgreSQL; overkill for local deployment

## References
- ChromaDB REST API: https://docs.trychroma.com/reference/rest-api
- Issue tracker for _type bug: chromadb/chromadb#1234
