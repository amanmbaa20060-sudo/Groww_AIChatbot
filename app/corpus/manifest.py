from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=1)
def _manifest_data(manifest_path: str = "corpus/url_manifest.yaml") -> dict[str, Any]:
    """
    Phase 0 single source of truth for which URLs may be cited and ingested.

    Keep this loader small and dependency-light so both ingestion and runtime can use it.
    """
    p = Path(manifest_path)
    data: dict[str, Any] = {}
    if p.is_file():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data


@lru_cache(maxsize=1)
def allowlisted_scheme_urls(manifest_path: str = "corpus/url_manifest.yaml") -> frozenset[str]:
    data = _manifest_data(manifest_path)

    schemes = data.get("schemes")
    if not isinstance(schemes, list):
        return frozenset()

    urls: set[str] = set()
    for row in schemes:
        if not isinstance(row, dict):
            continue
        u = row.get("groww_scheme_url")
        if isinstance(u, str) and u.strip():
            urls.add(u.strip())
    return frozenset(urls)


@lru_cache(maxsize=1)
def allowlisted_schemes(manifest_path: str = "corpus/url_manifest.yaml") -> list[dict[str, str]]:
    """
    Returns a minimal list of schemes for UI/prompts:
    [{scheme_id, display_name, slug, groww_scheme_url}, ...]
    """
    data = _manifest_data(manifest_path)
    schemes = data.get("schemes")
    if not isinstance(schemes, list):
        return []
    out: list[dict[str, str]] = []
    for row in schemes:
        if not isinstance(row, dict):
            continue
        sid = row.get("scheme_id")
        dn = row.get("display_name")
        slug = row.get("slug")
        url = row.get("groww_scheme_url")
        if isinstance(sid, str) and isinstance(dn, str) and isinstance(slug, str) and isinstance(url, str):
            out.append({"scheme_id": sid, "display_name": dn, "slug": slug, "groww_scheme_url": url})
    return out


def is_allowlisted_url(url: str | None) -> bool:
    if not url or not isinstance(url, str):
        return False
    return url in allowlisted_scheme_urls()

