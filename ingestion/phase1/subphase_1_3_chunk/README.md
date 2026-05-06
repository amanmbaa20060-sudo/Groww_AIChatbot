# Subphase 1.3 — Chunk + metadata

Reads `data/normalized/<scheme_id>/normalized.json`, splits `text` into overlapping windows (~1800 chars, overlap 250 by default), strips `<<<SECTION:…>>>` from chunk bodies, attaches:

- `chunk_id`, `chunk_index`, `scheme_id`, `scheme_ids`, `source_url` (manifest URL), `doc_type`, `section_path`, `text`, `char_count`

Writes **`data/chunks/<scheme_id>/chunks.jsonl`** (one JSON object per line).

```bash
python -m ingestion.phase1.subphase_1_3_chunk
python -m ingestion.phase1.subphase_1_3_chunk --target-chars 2200 --overlap 300
```

Requires Phase **1.2** output.
