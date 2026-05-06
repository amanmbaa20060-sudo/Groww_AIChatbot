"""
CLI utility for Phase 2 retrieval + answer assembly.

Example:
  python -m app.rag.cli --query "What is the exit load?" --scheme-id hdfc_mid_cap_direct_growth
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.rag.answer import answer_query


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 2 — Retrieve + answer from closed corpus.")
    p.add_argument("--query", required=True, help="User question (facts-only).")
    p.add_argument("--scheme-id", action="append", help="Optional scheme_id filter (repeatable).")
    p.add_argument("--chunks-root", type=Path, default=Path("data/chunks"), help="Path to data/chunks/")
    p.add_argument(
        "--latest-batch",
        type=Path,
        default=Path("data/registry/latest_batch.json"),
        help="Path to registry latest_batch.json (for footer date).",
    )
    p.add_argument("--top-k", type=int, default=5)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    scheme_filter = set(args.scheme_id) if args.scheme_id else None
    res = answer_query(
        query=str(args.query),
        chunks_root=args.chunks_root,
        registry_latest_path=args.latest_batch,
        top_k=int(args.top_k),
        scheme_filter=scheme_filter,
    )
    if res.citation_url:
        print(f"{res.answer_text}\n\nSource: {res.citation_url}\nLast updated from sources: {res.last_updated_utc_date}")
    else:
        print(res.answer_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

