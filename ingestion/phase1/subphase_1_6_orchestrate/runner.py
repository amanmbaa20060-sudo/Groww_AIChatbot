"""
Phase 1.6 — Metadata registry + orchestration (docs/phase-wise-architecture.md §4.3).

Responsibilities:
- Run 1.1 → 1.5 in order (single CLI) with structured logging and non-zero exit on failure.
- Persist URL-level metadata (last_fetch, content hash, optional ETag/Last-Modified).
- Record ingestion batch date (UTC) per docs/last-updated-policy.md.

This runner is intentionally dependency-free and uses Phase 1 subphase modules directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ingestion.phase1.common.manifest import iter_scheme_targets, load_manifest
from ingestion.phase1.common.paths import repo_root
from ingestion.phase1.subphase_1_1_fetch.runner import main as fetch_main
from ingestion.phase1.subphase_1_2_parse.runner import main as parse_main
from ingestion.phase1.subphase_1_3_chunk.runner import main as chunk_main
from ingestion.phase1.subphase_1_4_embed.runner import main as embed_main
from ingestion.phase1.subphase_1_5_index.runner import main as index_main

LOGGER = logging.getLogger(__name__)

REPO_ROOT = repo_root()
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"
DEFAULT_RAW = REPO_ROOT / "data" / "raw"
DEFAULT_REGISTRY = REPO_ROOT / "data" / "registry"
DEFAULT_INDEX_DIR = REPO_ROOT / "data" / "index"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _batch_date_utc() -> str:
    # docs/last-updated-policy.md: UTC calendar date of ingestion batch
    return datetime.now(timezone.utc).date().isoformat()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class SchemeRegistryRow:
    scheme_id: str
    source_url: str
    last_fetch_utc: str | None
    http_status: int | None
    etag: str | None
    last_modified: str | None
    content_sha256: str | None
    raw_body_path: str | None
    raw_headers_path: str | None


def build_registry(
    *,
    manifest_path: Path,
    raw_dir: Path,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    targets = iter_scheme_targets(manifest)

    rows: list[dict[str, Any]] = []
    for t in targets:
        headers_path = raw_dir / t.scheme_id / "headers.json"
        body_path = raw_dir / t.scheme_id / "body.html"

        hdr: dict[str, Any] | None = None
        if headers_path.is_file():
            hdr = json.loads(headers_path.read_text(encoding="utf-8"))

        last_fetch = hdr.get("fetched_at_utc") if isinstance(hdr, dict) else None
        http_status = hdr.get("http_status") if isinstance(hdr, dict) else None
        etag = hdr.get("etag") if isinstance(hdr, dict) else None
        last_modified = hdr.get("last-modified") if isinstance(hdr, dict) else None

        content_hash = _sha256_file(body_path) if body_path.is_file() else None
        row = SchemeRegistryRow(
            scheme_id=t.scheme_id,
            source_url=t.groww_scheme_url,
            last_fetch_utc=str(last_fetch) if last_fetch is not None else None,
            http_status=int(http_status) if isinstance(http_status, int) else None,
            etag=str(etag) if etag is not None else None,
            last_modified=str(last_modified) if last_modified is not None else None,
            content_sha256=content_hash,
            raw_body_path=str(body_path) if body_path.exists() else None,
            raw_headers_path=str(headers_path) if headers_path.exists() else None,
        )
        rows.append(row.__dict__)

    return {
        "phase": "1.6",
        "generated_at_utc": _utc_now_iso(),
        "schemes": rows,
    }


def _patch_index_meta_with_batch(
    *,
    index_dir: Path,
    index_name: str,
    ingestion_batch_date_utc: str,
    ingestion_batch_id: str,
) -> None:
    meta_path = index_dir / index_name / "index_meta.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Missing index meta: {meta_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["ingestion_batch_date_utc"] = ingestion_batch_date_utc
    meta["ingestion_batch_id"] = ingestion_batch_id
    meta["orchestrated_at_utc"] = _utc_now_iso()
    _atomic_write_text(meta_path, json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def run_pipeline(args: argparse.Namespace) -> int:
    ingestion_batch_date_utc = _batch_date_utc()
    ingestion_batch_id = f"batch_{ingestion_batch_date_utc}_{int(time.time())}"

    # Run subphases in order; failures propagate as non-zero.
    if not args.skip_1_1:
        LOGGER.info("Running 1.1 fetch...")
        rc = fetch_main(["--manifest", str(args.manifest)] + (["--ignore-robots"] if args.ignore_robots else []))
        if rc != 0:
            return rc

    if not args.skip_1_2:
        LOGGER.info("Running 1.2 parse...")
        rc = parse_main(["--manifest", str(args.manifest)])
        if rc != 0:
            return rc

    if not args.skip_1_3:
        LOGGER.info("Running 1.3 chunk...")
        rc = chunk_main(["--manifest", str(args.manifest)])
        if rc != 0:
            return rc

    if not args.skip_1_4:
        LOGGER.info("Running 1.4 embed...")
        # Do not pass --resume by default: after 1.3 re-chunk, chunk text can change while chunk_id stays
        # the same; resume would skip re-embed and leave vectors misaligned with chunks (wrong retrieval).
        embed_argv = ["--manifest", str(args.manifest)]
        if args.embed_resume:
            embed_argv.append("--resume")
        rc = embed_main(embed_argv)
        if rc != 0:
            return rc

    if not args.skip_1_5:
        LOGGER.info("Running 1.5 index build...")
        rc = index_main(
            [
                "--manifest",
                str(args.manifest),
                "--index-name",
                str(args.index_name),
                "--embedding-dim",
                str(args.embedding_dim),
                "--embedding-model",
                str(args.embedding_model),
            ]
        )
        if rc != 0:
            return rc

    # Registry build from raw cache (+ headers)
    LOGGER.info("Writing registry...")
    reg = build_registry(manifest_path=args.manifest, raw_dir=DEFAULT_RAW)
    reg["ingestion_batch_date_utc"] = ingestion_batch_date_utc
    reg["ingestion_batch_id"] = ingestion_batch_id
    reg_path = DEFAULT_REGISTRY / "url_registry.json"
    _atomic_write_text(reg_path, json.dumps(reg, ensure_ascii=False, indent=2) + "\n")

    latest_path = DEFAULT_REGISTRY / "latest_batch.json"
    latest = {
        "ingestion_batch_date_utc": ingestion_batch_date_utc,
        "ingestion_batch_id": ingestion_batch_id,
        "index_name": str(args.index_name),
        "index_meta_path": str(DEFAULT_INDEX_DIR / str(args.index_name) / "index_meta.json"),
        "written_at_utc": _utc_now_iso(),
    }
    _atomic_write_text(latest_path, json.dumps(latest, ensure_ascii=False, indent=2) + "\n")

    # Patch index_meta.json with batch date (policy hook)
    _patch_index_meta_with_batch(
        index_dir=DEFAULT_INDEX_DIR,
        index_name=str(args.index_name),
        ingestion_batch_date_utc=ingestion_batch_date_utc,
        ingestion_batch_id=ingestion_batch_id,
    )

    LOGGER.info("Pipeline complete. batch_date_utc=%s index_name=%s", ingestion_batch_date_utc, args.index_name)
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 1.6 — Run Phase 1 pipeline and write registry metadata.")
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to corpus/url_manifest.yaml")

    p.add_argument("--skip-1-1", action="store_true", help="Skip subphase 1.1 fetch")
    p.add_argument("--skip-1-2", action="store_true", help="Skip subphase 1.2 parse")
    p.add_argument("--skip-1-3", action="store_true", help="Skip subphase 1.3 chunk")
    p.add_argument("--skip-1-4", action="store_true", help="Skip subphase 1.4 embed")
    p.add_argument("--skip-1-5", action="store_true", help="Skip subphase 1.5 index")

    p.add_argument("--ignore-robots", action="store_true", help="Pass --ignore-robots to 1.1 (policy-dependent)")
    p.add_argument(
        "--embed-resume",
        action="store_true",
        help="Pass --resume to 1.4 (only new chunk_ids; unsafe after 1.3 text changes)",
    )

    # Index parameters (must match 1.4/1.5 defaults unless overridden)
    p.add_argument("--index-name", default="groww_hash_v1_dim768", help="Index name under data/index/")
    p.add_argument("--embedding-dim", type=int, default=768, help="Embedding dim for embed/index steps")
    p.add_argument(
        "--embedding-model",
        default="hash_v1_blake2b_salt=groww_rag_hash_v1_dim=768",
        help="Embedding model identifier (must match Phase 1.4)",
    )

    p.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    t0 = time.time()
    try:
        rc = run_pipeline(args)
    except Exception:
        LOGGER.exception("Phase 1.6 failed.")
        return 1
    finally:
        LOGGER.info("Elapsed: %.2fs", time.time() - t0)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
