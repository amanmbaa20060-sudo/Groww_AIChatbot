"""
Phase 3 CLI: query classification + safe routing.

Example:
  python -m app.guardrails.cli --query "What is the exit load?" --scheme-id hdfc_mid_cap_direct_growth
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.guardrails.phase3 import run_phase3


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 3 — Guardrails + routing.")
    p.add_argument("--query", required=True)
    p.add_argument("--scheme-id", action="append", help="Optional scheme_id filter (repeatable).")
    p.add_argument("--chunks-root", type=Path, default=Path("data/chunks"))
    p.add_argument("--latest-batch", type=Path, default=Path("data/registry/latest_batch.json"))
    p.add_argument("--use-groq", action="store_true", help="Use Groq LLM for factual answer generation (Phase 3).")
    p.add_argument("--groq-model", default="llama-3.1-8b-instant", help="Groq model name.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    scheme_filter = set(args.scheme_id) if args.scheme_id else None
    res = run_phase3(
        query=str(args.query),
        chunks_root=args.chunks_root,
        registry_latest_path=args.latest_batch,
        scheme_filter=scheme_filter,
        use_groq=bool(args.use_groq),
        groq_model=str(args.groq_model),
    )
    print(f"[{res.label}] {res.response}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

