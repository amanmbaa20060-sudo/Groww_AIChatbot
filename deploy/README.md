# Deployment and operations (Phase 6)

- Environments: dev / prod (minimal split).
- Secrets: API keys only via environment variables; never commit secrets.
- Corpus refresh: version manifest + index together (hash in artifact name or metadata).
- Observability: latency, errors, refusal rate aggregates (avoid logging raw PII or prompts if policy requires).

See `docs/phase-wise-architecture.md` §9 and `docs/edge-cases-phase-6.md`.

## Deploy backend to Render

This repo includes a Render blueprint: `render.yaml`.

### Steps

1. Push this repo to GitHub (already done).
2. In Render: **New + → Blueprint** → select your repo.
3. Set environment variables for the service:
   - `GROQ_API_KEY`: your Groq key (Render dashboard secret)
   - `GROQ_MODEL`: optional (defaults to `llama-3.1-8b-instant`)
4. Deploy.

### Health check

- `GET /health` returns:
  - `ok: true`
  - `data_ready: true|false` (whether `data/chunks/**/chunks.jsonl` exists on the server)

### Note about data artifacts

This project’s indexed artifacts (`data/chunks/`, `data/registry/`, etc.) are gitignored.
For production, you must either:
- Build and persist these artifacts on the server, or
- Store and load them from a separate artifact store.
