# API (Phase 2+)

Expose a small HTTP API for the chatbot. Contract: facts-only answers, ≤3 sentences, one manifest URL, footer date per `docs/last-updated-policy.md`.

## Implemented (Phase 4 backend)

A minimal stdlib HTTP server is implemented at `app/api/server.py`.

### Run

From repo root:

```bash
python -m app.api
```

### Endpoint

`POST /query`

Request:

```json
{"query":"What is the exit load?","scheme_ids":["hdfc_mid_cap_direct_growth"],"use_groq":false}
```

Response:

```json
{"label":"FACTUAL_MF","answer_text":"...","citation_url":"https://groww.in/...","last_updated_from_sources_utc":"YYYY-MM-DD"}
```

Policy: If label is `PERSONAL_INFO` or `UNKNOWN` (or `OUT_OF_SCOPE`/`AMBIGUOUS`), then `citation_url` is `null`.
