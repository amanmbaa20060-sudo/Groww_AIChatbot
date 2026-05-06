# Subphase 1.6 — Metadata registry + orchestration

Runs the full Phase 1 pipeline (1.1 → 1.5) and writes URL-level registry metadata + batch date (UTC) per `docs/last-updated-policy.md`.

## Outputs

- `data/registry/url_registry.json` — per-scheme metadata (fetch time, status, content hash, ETag/Last-Modified if present)
- `data/registry/latest_batch.json` — batch pointers (UTC date + index name)
- Updates `data/index/<index_name>/index_meta.json` to include:
  - `ingestion_batch_date_utc` (`YYYY-MM-DD`)
  - `ingestion_batch_id`

## Run

From repo root:

```bash
python -m ingestion.phase1.subphase_1_6_orchestrate
```

If you already have cached raw/normalized/chunks/embeddings and just want to rebuild the index + registry:

```bash
python -m ingestion.phase1.subphase_1_6_orchestrate --skip-1-1 --skip-1-2 --skip-1-3 --skip-1-4
```

# Subphase 1.6 — Metadata + orchestration

URL-level metadata (`last_fetch`, content hash), `ingestion_batch_id` / UTC date for `docs/last-updated-policy.md`, single job chaining 1.1→1.5.

**Status:** not implemented.
