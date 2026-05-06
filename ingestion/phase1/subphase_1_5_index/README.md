# Subphase 1.5 — Vector index build

Consumes Phase 1.4 outputs (`data/embeddings/<scheme_id>/embeddings.jsonl`) and builds a versioned, full-rebuild index:

- `data/index/<index_name>/vectors.f32` — raw float32 vectors (little-endian, row-major)
- `data/index/<index_name>/meta.jsonl` — metadata per row (`chunk_id`, `source_url`, …)
- `data/index/<index_name>/index_meta.json` — run summary and allowlist hash

## Run

From repo root (with venv activated, or use `.\.venv\Scripts\python.exe` on Windows):

```bash
python -m ingestion.phase1.subphase_1_5_index --dry-run
python -m ingestion.phase1.subphase_1_5_index
```

Or via shim:

```bash
python -m ingestion.index_build
```

## Notes

- Full rebuild: writes into a temporary folder and swaps it in, so stale vectors cannot linger.
- Closed corpus enforcement: validates `corpus/url_manifest.yaml` via `scripts/validate_manifest.py` and rejects any embedding row whose `source_url` is not the manifest URL for that scheme.
- A smoke retrieval runs automatically after build and checks that retrieved results have `source_url` ∈ the allowlist.

# Subphase 1.5 — Vector index build

Persist FAISS/Chroma (or chosen store); replace-by-URL or full rebuild.

**Status:** not implemented.
