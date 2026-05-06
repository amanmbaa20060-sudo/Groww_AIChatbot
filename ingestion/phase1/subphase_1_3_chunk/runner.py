"""
Phase 1.3 — Chunk + metadata (docs/phase-wise-architecture.md §4.3).

Reads `data/normalized/<scheme_id>/normalized.json`, emits `data/chunks/<scheme_id>/chunks.jsonl`.
Each line is a JSON object with chunk_id, source_url, scheme_id, section_path, doc_type, text.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ingestion.phase1.common.manifest import iter_scheme_targets, load_manifest
from ingestion.phase1.common.paths import repo_root
from ingestion.phase1.subphase_1_3_chunk.chunker import chunk_normalized_text

LOGGER = logging.getLogger(__name__)

REPO_ROOT = repo_root()
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"
DEFAULT_NORM = REPO_ROOT / "data" / "normalized"
DEFAULT_OUT = REPO_ROOT / "data" / "chunks"


def run_chunk(
    manifest_path: Path,
    norm_dir: Path,
    out_dir: Path,
    *,
    scheme_filter: str | None,
    target_chars: int,
    overlap: int,
) -> list[tuple[str, bool, str | None]]:
    manifest = load_manifest(manifest_path)
    targets = iter_scheme_targets(manifest)
    results: list[tuple[str, bool, str | None]] = []

    for t in targets:
        if scheme_filter and t.scheme_id != scheme_filter:
            continue
        norm_path = norm_dir / t.scheme_id / "normalized.json"
        if not norm_path.is_file():
            msg = f"missing {norm_path} (run Phase 1.2 first)"
            LOGGER.error("%s: %s", t.scheme_id, msg)
            results.append((t.scheme_id, False, msg))
            continue
        try:
            rec = json.loads(norm_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            results.append((t.scheme_id, False, str(exc)))
            continue

        text = rec.get("text") or ""
        if not isinstance(text, str) or not text.strip():
            results.append((t.scheme_id, False, "normalized.json has empty text"))
            continue

        source_url = rec.get("source_url") or t.groww_scheme_url
        doc_type = rec.get("doc_type") or "groww_scheme_page"
        if source_url != t.groww_scheme_url:
            LOGGER.warning("%s: source_url in JSON differs from manifest; using manifest URL", t.scheme_id)
            source_url = t.groww_scheme_url

        chunks = chunk_normalized_text(
            text,
            t.scheme_id,
            source_url,
            str(doc_type),
            target_chars=target_chars,
            overlap=overlap,
        )
        if not chunks:
            results.append((t.scheme_id, False, "chunker produced zero chunks"))
            continue

        if any(not c.get("source_url") for c in chunks):
            results.append((t.scheme_id, False, "chunk missing source_url"))
            continue

        dest = out_dir / t.scheme_id
        dest.mkdir(parents=True, exist_ok=True)
        out_path = dest / "chunks.jsonl"
        tmp = out_path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for ch in chunks:
                f.write(json.dumps(ch, ensure_ascii=False) + "\n")
        tmp.replace(out_path)
        LOGGER.info(
            "%s: %s chunks -> %s",
            t.scheme_id,
            len(chunks),
            out_path.relative_to(REPO_ROOT),
        )
        results.append((t.scheme_id, True, None))

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--norm-dir", type=Path, default=DEFAULT_NORM)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--scheme-id", type=str, default=None)
    parser.add_argument("--target-chars", type=int, default=1800)
    parser.add_argument("--overlap", type=int, default=250)
    parser.add_argument("-q", "--quiet", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    results = run_chunk(
        args.manifest,
        args.norm_dir,
        args.out_dir,
        scheme_filter=args.scheme_id,
        target_chars=args.target_chars,
        overlap=args.overlap,
    )
    if not results:
        return 1
    if sum(1 for _, ok, _ in results if ok) < len(results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
