# Ingestion — Phase 1 layout

All Phase 1 work lives under **`ingestion/phase1/`** (architecture §4.3).

```
ingestion/phase1/
  common/                    # manifest, repo paths
  subphase_1_1_fetch/        # ✅ 1.1 manifest → HTTP fetch
  subphase_1_2_parse/        # ✅ 1.2 parse + normalize
  subphase_1_3_chunk/        # ✅ 1.3 chunk + metadata
  subphase_1_4_embed/        # ✅ 1.4 embed
  subphase_1_5_index/        # ✅ 1.5 vector index
  subphase_1_6_orchestrate/  # ✅ 1.6 orchestration + registry
```

**Windows:** use `.\.venv\Scripts\python.exe` after `scripts\setup.ps1`.

## Commands (repo root)

```bash
python -m ingestion.phase1.subphase_1_1_fetch --ignore-robots
python -m ingestion.phase1.subphase_1_2_parse
python -m ingestion.phase1.subphase_1_3_chunk
python -m ingestion.phase1.subphase_1_4_embed --resume
python -m ingestion.phase1.subphase_1_5_index
python -m ingestion.phase1.subphase_1_6_orchestrate
```

Shims: `python -m ingestion.fetch` (1.1), `python -m ingestion.parse_chunk` (1.2), `python -m ingestion.chunk` (1.3), `python -m ingestion.embed` (1.4), `python -m ingestion.index_build` (1.5).

Artifacts: `data/raw/`, `data/normalized/`, `data/chunks/`, `data/embeddings/`, `data/index/`, `data/registry/` — see `data/README.md`.

Phase 0: `python scripts/validate_manifest.py` before first fetch.
