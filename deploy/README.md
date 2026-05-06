# Deployment and operations (Phase 6)

- Environments: dev / prod (minimal split).
- Secrets: API keys only via environment variables; never commit secrets.
- Corpus refresh: version manifest + index together (hash in artifact name or metadata).
- Observability: latency, errors, refusal rate aggregates (avoid logging raw PII or prompts if policy requires).

See `docs/phase-wise-architecture.md` §9 and `docs/edge-cases-phase-6.md`.
