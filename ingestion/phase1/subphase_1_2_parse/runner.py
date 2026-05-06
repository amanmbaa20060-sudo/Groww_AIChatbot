"""
Phase 1.2 — Parse → clean text (docs/phase-wise-architecture.md §4.3).

Reads `data/raw/<scheme_id>/body.html`, extracts Groww `__NEXT_DATA__` / `mfServerSideData`
when present, adds visible body text (BeautifulSoup), normalizes Unicode, dedupes lines,
writes `data/normalized/<scheme_id>/normalized.json`.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

from ingestion.phase1.common.manifest import iter_scheme_targets, load_manifest
from ingestion.phase1.common.paths import repo_root
from ingestion.phase1.subphase_1_2_parse.flatten import dedupe_consecutive_lines, mf_server_side_to_text
from ingestion.phase1.subphase_1_2_parse.html_clean import extract_visible_text
from ingestion.phase1.subphase_1_2_parse.next_data_extract import extract_mf_server_side

LOGGER = logging.getLogger(__name__)

REPO_ROOT = repo_root()
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_OUT = REPO_ROOT / "data" / "normalized"
SCHEMA_VERSION = "1"
MIN_TEXT_CHARS = 800  # soft floor; below this sets needs_review


def _title_from_html(html: str) -> str | None:
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if not m:
        return None
    return unicodedata.normalize("NFKC", m.group(1)).strip()


def parse_one_scheme(
    scheme_id: str,
    groww_scheme_url: str,
    display_name: str,
    raw_html_path: Path,
) -> dict:
    html = raw_html_path.read_text(encoding="utf-8", errors="replace")
    html = unicodedata.normalize("NFKC", html)

    ms = extract_mf_server_side(html)
    parts: list[str] = []
    next_present = ms is not None
    if ms:
        structured = mf_server_side_to_text(ms)
        structured = dedupe_consecutive_lines(structured)
        parts.append("=== STRUCTURED (mfServerSideData) ===\n" + structured)
    visible = extract_visible_text(html)
    if visible:
        parts.append("=== VISIBLE PAGE TEXT ===\n" + visible)

    full_text = "\n\n".join(parts).strip()
    full_text = dedupe_consecutive_lines(full_text)

    title = _title_from_html(html) or display_name
    needs_review = len(full_text) < MIN_TEXT_CHARS

    return {
        "schema_version": SCHEMA_VERSION,
        "scheme_id": scheme_id,
        "source_url": groww_scheme_url,
        "title": title,
        "display_name": display_name,
        "doc_type": "groww_scheme_page",
        "parsed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "next_data_present": next_present,
        "text_char_count": len(full_text),
        "needs_review": needs_review,
        "text": full_text,
    }


def run_parse(
    manifest_path: Path,
    raw_dir: Path,
    out_dir: Path,
    *,
    scheme_filter: str | None,
) -> list[tuple[str, bool, str | None]]:
    manifest = load_manifest(manifest_path)
    targets = iter_scheme_targets(manifest)
    results: list[tuple[str, bool, str | None]] = []

    for t in targets:
        if scheme_filter and t.scheme_id != scheme_filter:
            continue
        raw_path = raw_dir / t.scheme_id / "body.html"
        if not raw_path.is_file():
            msg = f"missing {raw_path} (run Phase 1.1 fetch first)"
            LOGGER.error("%s: %s", t.scheme_id, msg)
            results.append((t.scheme_id, False, msg))
            continue
        try:
            record = parse_one_scheme(
                t.scheme_id,
                t.groww_scheme_url,
                t.display_name,
                raw_path,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("parse failed %s", t.scheme_id)
            results.append((t.scheme_id, False, str(exc)))
            continue

        dest = out_dir / t.scheme_id
        dest.mkdir(parents=True, exist_ok=True)
        out_path = dest / "normalized.json"
        tmp = out_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(out_path)

        if record["needs_review"]:
            LOGGER.warning(
                "%s: text_char_count=%s below soft floor %s — flagged needs_review",
                t.scheme_id,
                record["text_char_count"],
                MIN_TEXT_CHARS,
            )
        else:
            LOGGER.info(
                "%s: wrote %s (%s chars, next_data=%s)",
                t.scheme_id,
                out_path.relative_to(REPO_ROOT),
                record["text_char_count"],
                record["next_data_present"],
            )
        results.append((t.scheme_id, True, None))

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scheme-id", type=str, default=None, help="Only this scheme_id")
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    results = run_parse(
        args.manifest,
        args.raw_dir,
        args.out_dir,
        scheme_filter=args.scheme_id,
    )
    if not results:
        LOGGER.error("No schemes processed (check --scheme-id or manifest)")
        return 1
    n_ok = sum(1 for _, ok, _ in results if ok)
    if n_ok < len(results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
