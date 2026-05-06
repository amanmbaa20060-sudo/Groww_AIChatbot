# Subphase 1.2 — Parse → clean text

Reads `data/raw/<scheme_id>/body.html`, extracts:

1. **`__NEXT_DATA__` → `mfServerSideData`** — flattened to labeled lines with `<<<SECTION:key>>>` sentinels for chunking.
2. **Visible body text** — via BeautifulSoup + `lxml` (scripts/styles removed, NFKC Unicode).

Writes **`data/normalized/<scheme_id>/normalized.json`** (`schema_version`, `text`, `source_url`, `needs_review` if very short, etc.).

```bash
python -m ingestion.phase1.subphase_1_2_parse
python -m ingestion.phase1.subphase_1_2_parse --scheme-id hdfc_mid_cap_direct_growth
```

Requires Phase **1.1** raw HTML. Dependencies: `beautifulsoup4`, `lxml` (see `requirements.txt`).
