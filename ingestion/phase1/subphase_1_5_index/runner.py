"""
Phase 1.5 — Vector index build (docs/phase-wise-architecture.md §4.3).

Builds a *versioned*, full-rebuild on-disk vector index from Phase 1.4 outputs:

- input:  data/embeddings/<scheme_id>/embeddings.jsonl
- output: data/index/<index_name>/
    - vectors.f32            (raw float32 vectors, row-major)
    - meta.jsonl             (one JSON metadata record per row, includes chunk_id + source_url)
    - index_meta.json        (run summary, allowlist hash, dimensions, counts)

This is a minimal, dependency-free index (brute-force cosine for smoke tests).
Later you can swap it for FAISS/Chroma while keeping the same artifact contract.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import math
import os
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from ingestion.phase1.common.manifest import iter_scheme_targets, load_manifest
from ingestion.phase1.common.paths import repo_root
from ingestion.phase1.subphase_1_4_embed.hash_embedder import hash_embed_to_float32_bytes

LOGGER = logging.getLogger(__name__)

REPO_ROOT = repo_root()
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"
DEFAULT_EMBED = REPO_ROOT / "data" / "embeddings"
DEFAULT_OUT = REPO_ROOT / "data" / "index"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_bytes(path: Path, b: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(b)
    tmp.replace(path)


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


def _hash_allowlist(allow: dict[str, str]) -> str:
    # Stable hash of {scheme_id: url} map to detect mismatched corpora
    items = sorted(allow.items())
    b = json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


@dataclass(frozen=True)
class IndexPaths:
    root: Path
    vectors_f32: Path
    meta_jsonl: Path
    index_meta_json: Path


def _paths(out_dir: Path, index_name: str) -> IndexPaths:
    root = out_dir / index_name
    return IndexPaths(
        root=root,
        vectors_f32=root / "vectors.f32",
        meta_jsonl=root / "meta.jsonl",
        index_meta_json=root / "index_meta.json",
    )


def _validate_embedding_row(
    row: dict[str, Any],
    *,
    scheme_id: str,
    allowed_url: str,
    embedding_dim: int,
    embedding_model: str,
) -> None:
    if row.get("scheme_id") != scheme_id:
        raise ValueError(f"Embedding scheme_id mismatch: expected {scheme_id}, got {row.get('scheme_id')!r}")
    if row.get("source_url") != allowed_url:
        raise ValueError(
            "Embedding source_url is not manifest-allowlisted "
            f"(expected {allowed_url}, got {row.get('source_url')!r})"
        )
    if row.get("embedding_dim") != embedding_dim:
        raise ValueError(
            f"Embedding dim mismatch: expected {embedding_dim}, got {row.get('embedding_dim')!r} "
            f"for chunk_id={row.get('chunk_id')!r}"
        )
    if row.get("embedding_model") != embedding_model:
        raise ValueError(
            f"Embedding model mismatch: expected {embedding_model}, got {row.get('embedding_model')!r} "
            f"for chunk_id={row.get('chunk_id')!r}"
        )
    if row.get("vector_format") != "base64_f32":
        raise ValueError(f"Unexpected vector_format={row.get('vector_format')!r}")
    if not isinstance(row.get("vector_b64"), str):
        raise ValueError("vector_b64 must be a string")
    if not isinstance(row.get("chunk_id"), str) or not row.get("chunk_id"):
        raise ValueError("chunk_id must be a non-empty string")


def _decode_vector_b64(vec_b64: str, *, embedding_dim: int) -> bytes:
    raw = base64.b64decode(vec_b64, validate=True)
    expected = 4 * embedding_dim
    if len(raw) != expected:
        raise ValueError(f"Vector byte length mismatch: expected {expected}, got {len(raw)}")
    return raw


def _cosine_sim(query_f32: bytes, doc_f32: bytes, *, dim: int) -> float:
    # Both are float32 bytes; compute cosine in Python (fast enough for smoke tests)
    fmt = "<" + ("f" * dim)
    q = struct.unpack(fmt, query_f32)
    d = struct.unpack(fmt, doc_f32)
    dot = 0.0
    qn = 0.0
    dn = 0.0
    for i in range(dim):
        qi = float(q[i])
        di = float(d[i])
        dot += qi * di
        qn += qi * qi
        dn += di * di
    if qn <= 0.0 or dn <= 0.0:
        return 0.0
    return dot / (math.sqrt(qn) * math.sqrt(dn))


def build_index(
    *,
    manifest_path: Path,
    embeddings_dir: Path,
    out_dir: Path,
    index_name: str,
    embedding_dim: int,
    embedding_model: str,
    dry_run: bool,
) -> int:
    # Closed corpus enforcement: Phase 0 validator is normative
    validator = REPO_ROOT / "scripts" / "validate_manifest.py"
    if validator.is_file():
        cmd = [sys.executable, str(validator), str(manifest_path)]
        LOGGER.info("Validating manifest via Phase 0 validator: %s", " ".join(cmd))
        subprocess.run(cmd, check=True)

    manifest = load_manifest(manifest_path)
    targets = iter_scheme_targets(manifest)
    allow = {t.scheme_id: t.groww_scheme_url for t in targets}
    allow_hash = _hash_allowlist(allow)

    paths = _paths(out_dir, index_name)

    # Full rebuild: write into temp dir then swap
    tmp_root = paths.root.with_name(paths.root.name + ".tmp")
    if tmp_root.exists():
        # best-effort cleanup if a prior run crashed
        for p in sorted(tmp_root.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
        try:
            tmp_root.rmdir()
        except OSError:
            pass
    tmp_root.mkdir(parents=True, exist_ok=True)
    tmp_vectors = tmp_root / "vectors.f32"
    tmp_meta = tmp_root / "meta.jsonl"
    tmp_index_meta = tmp_root / "index_meta.json"

    total = 0
    if dry_run:
        for t in targets:
            in_path = embeddings_dir / t.scheme_id / "embeddings.jsonl"
            if not in_path.is_file():
                raise FileNotFoundError(f"Missing embeddings for {t.scheme_id}: {in_path}")
        LOGGER.info("Dry-run OK: embeddings exist for all schemes (%d).", len(targets))
        return 0

    # Write vectors + meta
    with tmp_vectors.open("wb") as vec_f, tmp_meta.open("w", encoding="utf-8") as meta_f:
        for t in targets:
            in_path = embeddings_dir / t.scheme_id / "embeddings.jsonl"
            if not in_path.is_file():
                raise FileNotFoundError(f"Missing embeddings for {t.scheme_id}: {in_path}")
            for row in _iter_jsonl(in_path):
                _validate_embedding_row(
                    row,
                    scheme_id=t.scheme_id,
                    allowed_url=allow[t.scheme_id],
                    embedding_dim=embedding_dim,
                    embedding_model=embedding_model,
                )
                raw = _decode_vector_b64(row["vector_b64"], embedding_dim=embedding_dim)
                vec_f.write(raw)

                meta = {
                    "row": total,
                    "chunk_id": row["chunk_id"],
                    "scheme_id": t.scheme_id,
                    "source_url": allow[t.scheme_id],
                    "doc_type": row.get("doc_type"),
                    "section_path": row.get("section_path"),
                    "char_count": row.get("char_count"),
                }
                meta_f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                total += 1

    index_meta = {
        "phase": "1.5",
        "index_name": index_name,
        "built_at_utc": _utc_now_iso(),
        "embedding_model": embedding_model,
        "embedding_dim": embedding_dim,
        "rows": total,
        "allowlist_hash_sha256": allow_hash,
        "vector_format": "raw_f32_le",
        "vectors_file": "vectors.f32",
        "meta_file": "meta.jsonl",
    }
    _atomic_write_text(tmp_index_meta, json.dumps(index_meta, ensure_ascii=False, indent=2) + "\n")

    # Swap tmp_root -> paths.root
    if paths.root.exists():
        # remove old root to avoid lingering stale content
        for p in sorted(paths.root.rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
        try:
            paths.root.rmdir()
        except OSError:
            pass
    tmp_root.replace(paths.root)

    LOGGER.info("Index built: %s rows=%d", paths.root, total)

    # Smoke retrieval: embed a small query and run brute-force top-3
    q = "exit load and expense ratio"
    q_f32 = hash_embed_to_float32_bytes(q, dim=embedding_dim, salt=f"groww_rag_hash_v1_dim={embedding_dim}")

    # read vectors back, scan
    best: list[tuple[float, int]] = []  # (score, row)
    vec_bytes = paths.vectors_f32.read_bytes()
    row_bytes = 4 * embedding_dim
    if len(vec_bytes) != row_bytes * total:
        raise ValueError("vectors.f32 size does not match expected rows*dim")
    for i in range(total):
        d = vec_bytes[i * row_bytes : (i + 1) * row_bytes]
        s = _cosine_sim(q_f32, d, dim=embedding_dim)
        best.append((s, i))
    best.sort(reverse=True)
    top = best[:3]

    # Read meta lines for those rows
    metas: dict[int, dict[str, Any]] = {}
    want = {r for _, r in top}
    with paths.meta_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            r = int(m["row"])
            if r in want:
                metas[r] = m
                if len(metas) == len(want):
                    break

    for score, r in top:
        m = metas.get(r, {})
        if m.get("source_url") not in allow.values():
            raise ValueError("Smoke retrieval returned non-allowlisted source_url")
        LOGGER.info("Smoke top row=%s score=%.4f chunk_id=%s scheme_id=%s", r, score, m.get("chunk_id"), m.get("scheme_id"))

    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 1.5 — Build vector index from embeddings.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to corpus/url_manifest.yaml")
    p.add_argument("--embeddings-dir", type=Path, default=DEFAULT_EMBED, help="Directory containing data/embeddings/")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Output directory (default: data/index)")
    p.add_argument("--index-name", default="groww_hash_v1_dim768", help="Versioned index folder name under out-dir")
    p.add_argument("--embedding-dim", type=int, default=768, help="Embedding dimension (must match Phase 1.4)")
    p.add_argument(
        "--embedding-model",
        default="hash_v1_blake2b_salt=groww_rag_hash_v1_dim=768",
        help="Embedding model identifier (must match Phase 1.4)",
    )
    p.add_argument("--dry-run", action="store_true", help="Validate inputs only; do not write index")
    p.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    t0 = time.time()
    rc = build_index(
        manifest_path=args.manifest,
        embeddings_dir=args.embeddings_dir,
        out_dir=args.out_dir,
        index_name=str(args.index_name),
        embedding_dim=int(args.embedding_dim),
        embedding_model=str(args.embedding_model),
        dry_run=bool(args.dry_run),
    )
    LOGGER.info("Elapsed: %.2fs", time.time() - t0)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
