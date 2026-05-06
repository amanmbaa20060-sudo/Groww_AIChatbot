# Phase 1 — Ingestion layout

| Folder | Subphase | Status |
|--------|----------|--------|
| `common/` | Shared | Manifest loader used by 1.1+ |
| `subphase_1_1_fetch/` | **1.1** Manifest → fetch | Implemented |
| `subphase_1_2_parse/` | **1.2** Parse → clean text | Implemented |
| `subphase_1_3_chunk/` | **1.3** Chunk + metadata | Implemented |
| `subphase_1_4_embed/` | **1.4** Embed | Implemented |
| `subphase_1_5_index/` | **1.5** Vector index | Implemented |
| `subphase_1_6_orchestrate/` | **1.6** Metadata + pipeline | Implemented |

## Run 1.1

From repository root (with venv activated or `.\.venv\Scripts\python.exe` on Windows):

```bash
python -m ingestion.phase1.subphase_1_1_fetch --dry-run
python -m ingestion.phase1.subphase_1_1_fetch
```

Shim (same behaviour): `python -m ingestion.fetch`

## Run 1.2 → 1.3

```bash
python -m ingestion.phase1.subphase_1_2_parse
python -m ingestion.phase1.subphase_1_3_chunk
```

## Run 1.4

```bash
python -m ingestion.phase1.subphase_1_4_embed --dry-run
python -m ingestion.phase1.subphase_1_4_embed --resume
```

## Run 1.5

```bash
python -m ingestion.phase1.subphase_1_5_index --dry-run
python -m ingestion.phase1.subphase_1_5_index
```

See each subfolder `README.md` for flags. Shims: `python -m ingestion.parse_chunk` (1.2), `python -m ingestion.chunk` (1.3), `python -m ingestion.embed` (1.4), `python -m ingestion.index_build` (1.5).

## Run 1.6

```bash
python -m ingestion.phase1.subphase_1_6_orchestrate
```
