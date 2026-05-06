# Application package

| Folder | Phase | Role |
|--------|-------|------|
| `api/` | 2+ | HTTP `/chat` or `/query` entrypoints |
| `rag/` | 2 | Retrieve, generate, post-validate citations |
| `guardrails/` | 3 | Query classification + refusal templates |
| `ui/` | 4 | Minimal web UI (or static assets served by API) |

See `docs/phase-wise-architecture.md`.
