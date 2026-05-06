"""
Phase 1.1 — Manifest → fetch (docs/phase-wise-architecture.md §4.3).

- Validates manifest via `scripts/validate_manifest.py`
- HTTP GET only `groww_scheme_url` values from `corpus/url_manifest.yaml`
- Retries, timeout, identifiable User-Agent
- Persists raw body + selected headers per `scheme_id` under `--output-dir`
- On failure after retries: does not remove existing cached `body.html` (overwrite-on-success only)
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from ingestion.phase1.common.manifest import iter_scheme_targets, load_manifest
from ingestion.phase1.common.paths import repo_root

LOGGER = logging.getLogger(__name__)

USER_AGENT = "GrowwRAGChatbotM2/1.0 (phase-1.1-fetch; HDFC MF facts-only FAQ corpus)"

REPO_ROOT = repo_root()
DEFAULT_MANIFEST = REPO_ROOT / "corpus" / "url_manifest.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "raw"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_manifest.py"

RETRYABLE_HTTP = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    scheme_id: str
    url: str
    ok: bool
    status: int | None
    error: str | None
    bytes_written: int | None
    output_dir: Path | None


def _headers_to_store(msg: Message, final_url: str, status: int) -> dict[str, Any]:
    keys = ("etag", "last-modified", "content-type", "date", "cache-control")
    h: dict[str, Any] = {
        "http_status": status,
        "final_url": final_url,
    }
    for k in keys:
        v = msg.get(k)
        if v is not None:
            h[k] = v
    return h


def _robots_allows(url: str, ua: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Could not read robots.txt (%s): %s", robots_url, exc)
        return True
    try:
        return rp.can_fetch(ua, url)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("robots can_fetch failed for %s: %s", url, exc)
        return True


def _fetch_once(url: str, timeout: float) -> tuple[int, bytes, Message, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        body = resp.read()
        status = getattr(resp, "status", 200)
        headers = resp.headers
        final = resp.geturl() or url
        return status, body, headers, final


def fetch_url(
    url: str,
    *,
    timeout: float,
    max_retries: int,
) -> tuple[bool, int | None, bytes | None, Message | None, str | None, str | None]:
    last_err: str | None = None
    for attempt in range(max_retries):
        try:
            status, body, headers, final = _fetch_once(url, timeout)
            if status in RETRYABLE_HTTP and attempt < max_retries - 1:
                wait = min(2**attempt, 16)
                LOGGER.warning("HTTP %s for %s; retry in %ss", status, url, wait)
                time.sleep(wait)
                continue
            if status >= 400:
                return False, status, body, headers, final, f"HTTP {status}"
            return True, status, body, headers, final, None
        except HTTPError as e:
            code = e.code
            if code in RETRYABLE_HTTP and attempt < max_retries - 1:
                wait = min(2**attempt, 16)
                LOGGER.warning("HTTPError %s for %s; retry in %ss", code, url, wait)
                time.sleep(wait)
                continue
            last_err = f"HTTPError {code}: {e.reason}"
            return False, code, None, None, None, last_err
        except URLError as e:
            last_err = f"URLError: {e.reason!r}"
            if attempt < max_retries - 1:
                wait = min(2**attempt, 16)
                LOGGER.warning("URLError for %s; retry in %ss: %s", url, wait, last_err)
                time.sleep(wait)
                continue
            return False, None, None, None, None, last_err
        except TimeoutError:
            last_err = "TimeoutError"
            if attempt < max_retries - 1:
                wait = min(2**attempt, 16)
                LOGGER.warning("Timeout for %s; retry in %ss", url, wait)
                time.sleep(wait)
                continue
            return False, None, None, None, None, last_err
    return False, None, None, None, None, last_err or "unknown error"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def _atomic_write_json(path: Path, obj: Any) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_bytes(path, text.encode("utf-8"))


def run_validate_manifest(manifest_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATE_SCRIPT), str(manifest_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout or "")
        sys.stderr.write(proc.stderr or "")
        raise SystemExit(proc.returncode or 1)


def fetch_all(
    manifest_path: Path,
    output_dir: Path,
    *,
    dry_run: bool,
    timeout: float,
    max_retries: int,
    ignore_robots: bool,
) -> list[FetchResult]:
    manifest = load_manifest(manifest_path)
    targets = iter_scheme_targets(manifest)
    results: list[FetchResult] = []

    for t in targets:
        out_sub = output_dir / t.scheme_id
        body_path = out_sub / "body.html"
        headers_path = out_sub / "headers.json"
        error_path = out_sub / "fetch_error.json"

        if dry_run:
            LOGGER.info("[dry-run] would fetch %s -> %s", t.groww_scheme_url, out_sub)
            results.append(
                FetchResult(t.scheme_id, t.groww_scheme_url, True, None, None, None, out_sub)
            )
            continue

        if not ignore_robots and not _robots_allows(t.groww_scheme_url, USER_AGENT):
            err = "Blocked by robots.txt for this User-Agent (use --ignore-robots to override)."
            LOGGER.error("%s: %s", t.scheme_id, err)
            _atomic_write_json(
                error_path,
                {
                    "scheme_id": t.scheme_id,
                    "url": t.groww_scheme_url,
                    "error": err,
                    "fetched_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            )
            results.append(
                FetchResult(t.scheme_id, t.groww_scheme_url, False, None, err, None, out_sub)
            )
            continue

        ok, status, body, hdrs, final_url, err = fetch_url(
            t.groww_scheme_url, timeout=timeout, max_retries=max_retries
        )
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if ok and body is not None and hdrs is not None and status is not None:
            _atomic_write_bytes(body_path, body)
            meta = _headers_to_store(hdrs, final_url or t.groww_scheme_url, status)
            meta["fetched_at_utc"] = now
            meta["request_url"] = t.groww_scheme_url
            meta["scheme_id"] = t.scheme_id
            _atomic_write_json(headers_path, meta)
            if error_path.exists():
                error_path.unlink(missing_ok=True)
            results.append(
                FetchResult(
                    t.scheme_id,
                    t.groww_scheme_url,
                    True,
                    status,
                    None,
                    len(body),
                    out_sub,
                )
            )
            LOGGER.info("OK %s (%s bytes, HTTP %s)", t.scheme_id, len(body), status)
        else:
            _atomic_write_json(
                error_path,
                {
                    "scheme_id": t.scheme_id,
                    "url": t.groww_scheme_url,
                    "http_status": status,
                    "error": err,
                    "fetched_at_utc": now,
                },
            )
            LOGGER.error("FAIL %s: %s", t.scheme_id, err)
            results.append(
                FetchResult(t.scheme_id, t.groww_scheme_url, False, status, err, None, out_sub)
            )

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to url_manifest.yaml",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory to store raw HTML + headers (per scheme_id subfolder)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate manifest and print targets; no HTTP requests",
    )
    parser.add_argument("--timeout", type=float, default=45.0, help="Per-request timeout (s)")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="Maximum attempts per URL (including first try)",
    )
    parser.add_argument(
        "--ignore-robots",
        action="store_true",
        help="Skip robots.txt gate (default: obey robots.txt)",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Exit 0 even if some fetches failed",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Warnings and errors only")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    run_validate_manifest(args.manifest)

    if args.dry_run:
        targets = iter_scheme_targets(load_manifest(args.manifest))
        print(f"Dry run: {len(targets)} URLs from {args.manifest}")
        for t in targets:
            print(f"  {t.scheme_id}\n    {t.groww_scheme_url}")
        print(f"Would write under: {args.output_dir.resolve()}")
        return 0

    results = fetch_all(
        args.manifest,
        args.output_dir,
        dry_run=False,
        timeout=args.timeout,
        max_retries=args.max_retries,
        ignore_robots=args.ignore_robots,
    )
    n_ok = sum(1 for r in results if r.ok)
    n_fail = len(results) - n_ok
    LOGGER.info("Done: %s ok, %s failed (of %s)", n_ok, n_fail, len(results))
    if n_fail and not args.allow_partial:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
