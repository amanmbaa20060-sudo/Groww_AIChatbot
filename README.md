# Groww RAG Chatbot (M2)

Facts-only mutual fund FAQ assistant (RAG), scoped to **HDFC Mutual Fund** schemes on a **fixed set of seventeen Groww scheme pages**. See `docs/problemstatement.md` and `docs/phase-wise-architecture.md`.

Requires **Python 3.10+** (`pyproject.toml`).

## Windows: `python` / `pip` not found (fix)

If `python --version` fails or opens the Microsoft Store, you are usually hitting the **WindowsApps stub** (`...\WindowsApps\python.exe`), not a real install. **You can still use this project:** `scripts\setup.ps1` looks for a real **python.org** install under `%LocalAppData%\Programs\Python\Python*\python.exe` (for example `Python312-arm64`) *before* giving up, so you often do **not** need to fix PATH first.

1. *(Recommended)* Turn off Store aliases: **Settings → Apps → Advanced app settings → App execution aliases** → disable **python.exe** / **python3.exe** so `python` is not hijacked later.
2. Install Python **3.10+** from [python.org](https://www.python.org/downloads/windows/) if you do not already have it under `%LocalAppData%\Programs\Python\`.
3. From this repository root, create a venv and install deps:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
   ```

4. In Cursor / VS Code: **Python: Select Interpreter** → **`.venv\Scripts\python.exe`** (see `.vscode/settings.json`).

**One-shot Phase 1.1** (runs `setup.ps1` first if `.venv` is missing):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_phase_1_1.ps1 -- --dry-run
powershell -ExecutionPolicy Bypass -File scripts/run_phase_1_1.ps1 -- --ignore-robots
```

After setup, prefer the venv for commands (plain `python` may still be the Store stub):

```powershell
.\.venv\Scripts\python.exe scripts\validate_manifest.py
.\.venv\Scripts\python.exe -m ingestion.phase1.subphase_1_1_fetch --dry-run
```

## Repository layout

| Path | Phase | Description |
|------|-------|-------------|
| `docs/` | 0+ | Problem statement, architecture, edge cases, content policy, compliance checklist |
| `corpus/` | **0** | `url_manifest.yaml` — closed corpus allowlist + scheme metadata |
| `scripts/` | **0** | `validate_manifest.py` — CI-friendly manifest checks |
| `ingestion/phase1/` | 1 | Subphases 1.1–1.6 (1.1 fetch implemented; rest stubs) |
| `app/api`, `app/rag`, `app/guardrails`, `app/ui` | 2–4 | Runtime (README placeholders) |
| `tests/golden`, `tests/test_refusals.py` | 3–5 | Eval and refusals (minimal placeholder) |
| `deploy/` | 6 | Ops notes |

## Phase 0 quickstart

**Windows (recommended):** run `scripts\setup.ps1` first, then use `.\.venv\Scripts\python.exe` as below.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/validate_manifest.py
```

**Any OS** (if `python` is already a real 3.10+):

```bash
pip install -r requirements.txt
python scripts/validate_manifest.py
```

Complete the sign-off table in `docs/compliance-checklist.md` before building Phase 1.

## Phase 1.1 — Fetch raw HTML

After Phase 0 validation (use your venv `python` on Windows, e.g. `.\.venv\Scripts\python.exe`):

```bash
python -m ingestion.phase1.subphase_1_1_fetch --dry-run
python -m ingestion.phase1.subphase_1_1_fetch
# equivalent: python -m ingestion.fetch
```

Outputs under `data/raw/` (see `data/README.md`). If `robots.txt` denies the default bot UA, use `--ignore-robots` only where policy allows.

## Phase 1.2 & 1.3 — Parse and chunk

After **1.1** raw HTML exists:

```bash
python -m ingestion.phase1.subphase_1_2_parse
python -m ingestion.phase1.subphase_1_3_chunk
```

Outputs: `data/normalized/<scheme_id>/normalized.json` and `data/chunks/<scheme_id>/chunks.jsonl` (see `data/README.md`).

## Phase 1.4 — Embed

After **1.3** chunks exist:

```bash
python -m ingestion.phase1.subphase_1_4_embed --dry-run
python -m ingestion.phase1.subphase_1_4_embed --resume
```

Outputs: `data/embeddings/<scheme_id>/embeddings.jsonl` (see `data/README.md`).

## Phase 1.5 — Vector index build

After **1.4** embeddings exist:

```bash
python -m ingestion.phase1.subphase_1_5_index --dry-run
python -m ingestion.phase1.subphase_1_5_index
# equivalent: python -m ingestion.index_build
```

Outputs: `data/index/<index_name>/` (see `data/README.md`).

## Phase 1.6 — Metadata registry + orchestration

Runs the full Phase 1 pipeline and writes batch metadata for the user-facing “Last updated from sources” footer (UTC date).

```bash
python -m ingestion.phase1.subphase_1_6_orchestrate
```

Outputs: `data/registry/` and updates `data/index/<index_name>/index_meta.json` with `ingestion_batch_date_utc`.

## Disclaimer

Facts-only. No investment advice.

## LLM provider (Phase 2+)

This project uses **Groq** for LLM calls in Phase 2+ (grounded generation) and potentially Phase 3 (LLM-assisted classification).

- Set `GROQ_API_KEY` in your environment (or CI secrets).
- Never commit API keys to the repo.
