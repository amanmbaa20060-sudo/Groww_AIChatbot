"""
Phase 1.4 — Embed (docs/phase-wise-architecture.md §4.3).

Reads `data/chunks/<scheme_id>/chunks.jsonl`, embeds each chunk `text`,
and writes `data/embeddings/<scheme_id>/embeddings.jsonl`.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ingestion.phase1.common.manifest import iter_scheme_targets, load_manifest
from ingestion.phase1.common.paths import repo_root
from ingestion.phase1.subphase_1_4_embed.hash_embedder import hash_embed_to_base64

LOGGER = logging.getLogger(__name__)

REPO_ROOT = repo_root()
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"
DEFAULT_CHUNKS = REPO_ROOT / "data" / "chunks"
DEFAULT_OUT = REPO_ROOT / "data" / "embeddings"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _load_existing_chunk_ids(out_jsonl: Path) -> set[str]:
    if not out_jsonl.is_file():
        return set()
    seen: set[str] = set()
    with out_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = obj.get("chunk_id")
            if isinstance(cid, str):
                seen.add(cid)
    return seen


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSONL at {path} line {ln}: {e}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object at {path} line {ln}")
            yield obj


def _validate_chunk_row(
    row: dict[str, Any],
    *,
    scheme_id: str,
    allowed_url: str,
) -> None:
    if row.get("scheme_id") != scheme_id:
        raise ValueError(f"Chunk scheme_id mismatch: expected {scheme_id}, got {row.get('scheme_id')!r}")
    if row.get("source_url") != allowed_url:
        raise ValueError(
            "Chunk source_url is not manifest-allowlisted "
            f"(expected {allowed_url}, got {row.get('source_url')!r})"
        )
    for k in ("chunk_id", "doc_type", "section_path", "text", "char_count"):
        if k not in row:
            raise ValueError(f"Chunk missing required field: {k}")
    if not isinstance(row["chunk_id"], str) or not row["chunk_id"]:
        raise ValueError("chunk_id must be a non-empty string")
    if not isinstance(row["text"], str):
        raise ValueError("text must be a string")


def embed_scheme(
    *,
    scheme_id: str,
    allowed_url: str,
    chunks_dir: Path,
    out_dir: Path,
    embedding_model: str,
    embedding_dim: int,
    salt: str,
    resume: bool,
) -> tuple[int, int]:
    in_path = chunks_dir / scheme_id / "chunks.jsonl"
    if not in_path.is_file():
        raise FileNotFoundError(f"Missing chunks.jsonl for {scheme_id}: {in_path}")

    out_path = out_dir / scheme_id / "embeddings.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_chunk_ids(out_path) if resume else set()
    embedded_at = _utc_now_iso()

    wrote = 0
    skipped = 0
    # Full rebuild must truncate; append-only would duplicate rows or keep stale vectors for unchanged chunk_ids.
    out_mode = "a" if resume else "w"
    with out_path.open(out_mode, encoding="utf-8") as out_f:
        for row in _iter_jsonl(in_path):
            _validate_chunk_row(row, scheme_id=scheme_id, allowed_url=allowed_url)
            cid = row["chunk_id"]
            if cid in existing:
                skipped += 1
                continue

            vec_b64 = hash_embed_to_base64(row["text"], dim=embedding_dim, salt=salt)
            rec = {
                "chunk_id": cid,
                "scheme_id": scheme_id,
                "source_url": allowed_url,
                "doc_type": row.get("doc_type"),
                "section_path": row.get("section_path"),
                "char_count": row.get("char_count"),
                "embedding_model": embedding_model,
                "embedding_dim": embedding_dim,
                "embedded_at_utc": embedded_at,
                "vector_b64": vec_b64,
                "vector_format": "base64_f32",
            }
            out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            wrote += 1

    return wrote, skipped


def run_embed(
    *,
    manifest_path: Path,
    chunks_dir: Path,
    out_dir: Path,
    embedding_dim: int,
    resume: bool,
    dry_run: bool,
) -> int:
    # Enforce closed-corpus allowlist (Phase 0 validator is normative)
    validator = REPO_ROOT / "scripts" / "validate_manifest.py"
    if validator.is_file():
        # validate_manifest.py expects a positional manifest path (no flag)
        cmd = [sys.executable, str(validator), str(manifest_path)]
        LOGGER.info("Validating manifest via Phase 0 validator: %s", " ".join(cmd))
        subprocess.run(cmd, check=True)

    manifest = load_manifest(manifest_path)
    targets = iter_scheme_targets(manifest)
    allow = {t.scheme_id: t.groww_scheme_url for t in targets}

    embedding_model = f"hash_v1_blake2b_salt={salt_for_model(embedding_dim)}"
    salt = salt_for_model(embedding_dim)

    total_wrote = 0
    total_skipped = 0

    for t in targets:
        LOGGER.info("Embedding scheme: %s", t.scheme_id)
        if dry_run:
            in_path = chunks_dir / t.scheme_id / "chunks.jsonl"
            if not in_path.is_file():
                raise FileNotFoundError(f"Missing chunks for {t.scheme_id}: {in_path}")
            continue

        wrote, skipped = embed_scheme(
            scheme_id=t.scheme_id,
            allowed_url=allow[t.scheme_id],
            chunks_dir=chunks_dir,
            out_dir=out_dir,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            salt=salt,
            resume=resume,
        )
        total_wrote += wrote
        total_skipped += skipped

    meta = {
        "phase": "1.4",
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dim,
        "embedded_at_utc": _utc_now_iso(),
        "total_written": total_wrote,
        "total_skipped_existing": total_skipped,
    }
    _atomic_write_text(out_dir / "embeddings_meta.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    LOGGER.info("Done. wrote=%s skipped=%s out=%s", total_wrote, total_skipped, out_dir)
    return 0


def salt_for_model(dim: int) -> str:
    # Include dimension to prevent silent dimension changes across runs.
    return f"groww_rag_hash_v1_dim={dim}"


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 1.4 — Embed chunks into vectors.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to corpus/url_manifest.yaml")
    p.add_argument("--chunks-dir", type=Path, default=DEFAULT_CHUNKS, help="Directory containing data/chunks/")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Output directory (default: data/embeddings)")
    p.add_argument("--embedding-dim", type=int, default=768, help="Embedding dimension for hash backend")
    p.add_argument("--resume", action="store_true", help="Skip already-embedded chunk_id records if output exists")
    p.add_argument("--dry-run", action="store_true", help="Validate inputs only; do not write embeddings")
    p.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    t0 = time.time()
    rc = run_embed(
        manifest_path=args.manifest,
        chunks_dir=args.chunks_dir,
        out_dir=args.out_dir,
        embedding_dim=args.embedding_dim,
        resume=bool(args.resume),
        dry_run=bool(args.dry_run),
    )
    LOGGER.info("Elapsed: %.2fs", time.time() - t0)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

