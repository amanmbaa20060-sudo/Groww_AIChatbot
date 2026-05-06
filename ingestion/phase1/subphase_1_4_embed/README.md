# Subphase 1.4 — Embed

Reads Phase 1.3 output (`data/chunks/<scheme_id>/chunks.jsonl`) and produces a per-scheme embeddings dataset:

- `data/embeddings/<scheme_id>/embeddings.jsonl` (one embedding record per chunk)
- `data/embeddings/embeddings_meta.json` (run summary)

## Run

From repo root (with venv activated, or use `.\.venv\Scripts\python.exe` on Windows):

```bash
python -m ingestion.phase1.subphase_1_4_embed --dry-run
python -m ingestion.phase1.subphase_1_4_embed --resume
```

## Notes

- This subphase enforces the **closed corpus** by validating `corpus/url_manifest.yaml` via `scripts/validate_manifest.py`
  and by rejecting any chunk whose `source_url` does not match the manifest URL for that scheme.
- The default embedding backend is a **deterministic local hash embedder** (no network calls), stored as base64-encoded
  float32 bytes (`vector_format: base64_f32`). This keeps Phase 1.4 mechanics correct and swappable when you pick a
  semantic embedding model later.

