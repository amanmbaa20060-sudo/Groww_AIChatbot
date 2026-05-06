#!/usr/bin/env python3
"""Validate corpus/url_manifest.yaml against Phase 0 rules (architecture §3.1)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Canonical allowlist — must match docs/phase-wise-architecture.md §3.1 exactly.
EXPECTED_URLS: frozenset[str] = frozenset(
    {
        "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-silver-etf-fof-direct-growth",
        "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-nifty-50-index-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
        "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-multi-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-short-term-opportunities-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-focused-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-pharma-and-healthcare-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-bse-sensex-index-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-large-and-mid-cap-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-liquid-fund-direct-growth",
        "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    }
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    if data.get("closed_corpus") is not True:
        errors.append("Field 'closed_corpus' must be true for this project.")

    amc = data.get("amc")
    if not isinstance(amc, dict):
        errors.append("Missing or invalid 'amc' object.")
    else:
        if amc.get("id") != "hdfc_mutual_fund":
            errors.append("amc.id must be 'hdfc_mutual_fund'.")
        if not amc.get("display_name"):
            errors.append("amc.display_name must be non-empty.")

    schemes = data.get("schemes")
    if not isinstance(schemes, list):
        errors.append("Missing or invalid 'schemes' list.")
        return errors

    if len(schemes) != 17:
        errors.append(f"Expected exactly 17 schemes, found {len(schemes)}.")

    seen_urls: set[str] = set()
    seen_ids: set[str] = set()

    required_keys = (
        "scheme_id",
        "slug",
        "display_name",
        "coarse_category",
        "groww_scheme_url",
        "source_type",
    )

    for i, row in enumerate(schemes):
        prefix = f"schemes[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: entry must be a mapping.")
            continue
        for k in required_keys:
            if k not in row or row[k] in (None, ""):
                errors.append(f"{prefix}: missing or empty '{k}'.")
        url = row.get("groww_scheme_url")
        if isinstance(url, str):
            if url in seen_urls:
                errors.append(f"{prefix}: duplicate URL {url!r}.")
            seen_urls.add(url)
            if url not in EXPECTED_URLS:
                errors.append(f"{prefix}: URL not in architecture §3.1 allowlist: {url!r}.")
            if not url.startswith("https://groww.in/"):
                errors.append(f"{prefix}: URL must start with https://groww.in/ : {url!r}.")
        st = row.get("source_type")
        if st != "groww_scheme_page":
            errors.append(f"{prefix}: source_type must be 'groww_scheme_page', got {st!r}.")
        sid = row.get("scheme_id")
        if isinstance(sid, str):
            if sid in seen_ids:
                errors.append(f"{prefix}: duplicate scheme_id {sid!r}.")
            seen_ids.add(sid)

    if len(schemes) == 17 and seen_urls != EXPECTED_URLS:
        missing = EXPECTED_URLS - seen_urls
        extra = seen_urls - EXPECTED_URLS
        if missing:
            errors.append(f"Missing URLs vs §3.1: {sorted(missing)}")
        if extra:
            errors.append(f"Unexpected URLs vs §3.1: {sorted(extra)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to url_manifest.yaml",
    )
    args = parser.parse_args()
    path: Path = args.manifest
    if not path.is_file():
        print(f"ERROR: manifest not found: {path}", file=sys.stderr)
        return 2

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        print("ERROR: root YAML must be a mapping.", file=sys.stderr)
        return 1

    errs = validate(data)
    if errs:
        print(f"Validation failed for {path}:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: {path} ({len(data['schemes'])} schemes, closed corpus).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
