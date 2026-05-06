# Subphase 1.1 — Manifest → fetch

Loads `corpus/url_manifest.yaml`, validates via `scripts/validate_manifest.py`, GETs only `groww_scheme_url` values, writes `data/raw/<scheme_id>/body.html` and `headers.json`.

```bash
python -m ingestion.phase1.subphase_1_1_fetch --dry-run
python -m ingestion.phase1.subphase_1_1_fetch
```

See `runner.py` for CLI flags (`--ignore-robots`, `--allow-partial`, …).
