# RAG runtime (Phase 2)

Retrieval over the Phase 1 artifacts, grounded answer assembly, citation post-validation against `corpus/url_manifest.yaml`.

## What’s implemented (current)

- **Lexical-first retrieval** over `data/chunks/<scheme_id>/chunks.jsonl` with section-aware boosting
- **Facts-only answer assembly** (no external LLM required yet)
- **Single citation**: uses the top hit’s `source_url`
- **Footer date**: reads `data/registry/latest_batch.json` (`ingestion_batch_date_utc`) per `docs/last-updated-policy.md`

## Run (CLI)

From repo root:

```bash
python -m app.rag.cli --query "What is the exit load?" --scheme-id hdfc_mid_cap_direct_growth
```

See `docs/phase-wise-architecture.md` §5 and `docs/edge-cases-phase-2.md`.
