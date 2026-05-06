# Data directory (generated)

| Path | Phase | Contents |
|------|-------|----------|
| `raw/<scheme_id>/` | **1.1** | `body.html` (raw response bytes), `headers.json` (subset of HTTP headers + `fetched_at_utc`), or `fetch_error.json` on failure |
| `normalized/<scheme_id>/` | **1.2** | `normalized.json` — structured + visible text, `source_url`, `needs_review` flag |
| `chunks/<scheme_id>/` | **1.3** | `chunks.jsonl` — one JSON chunk per line (`chunk_id`, `source_url`, `scheme_ids`, `text`, …) |
| `embeddings/<scheme_id>/` | **1.4** | `embeddings.jsonl` — one JSON embedding record per chunk (`chunk_id`, metadata, `vector_b64`, …) |
| `index/<index_name>/` | **1.5** | `vectors.f32`, `meta.jsonl`, `index_meta.json` |
| `registry/` | **1.6** | `url_registry.json`, `latest_batch.json` (includes `ingestion_batch_date_utc`) |

`data/raw/`, `data/normalized/`, `data/chunks/`, `data/embeddings/`, `data/index/`, and `data/registry/` are gitignored. Reproduce from the repository root:

```bash
python -m ingestion.phase1.subphase_1_1_fetch
python -m ingestion.phase1.subphase_1_2_parse
python -m ingestion.phase1.subphase_1_3_chunk
python -m ingestion.phase1.subphase_1_4_embed --resume
python -m ingestion.phase1.subphase_1_5_index
python -m ingestion.phase1.subphase_1_6_orchestrate --skip-1-1 --skip-1-2 --skip-1-3 --skip-1-4
```

Phase 1.1: use `--dry-run` to validate the manifest without HTTP calls.
