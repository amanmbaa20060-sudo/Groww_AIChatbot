"""Extract Next.js `__NEXT_DATA__` JSON from Groww HTML."""

from __future__ import annotations

import json
import re
from typing import Any

_NEXT_RE = re.compile(
    r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def extract_next_data_json(html: str) -> dict[str, Any] | None:
    m = _NEXT_RE.search(html)
    if not m:
        return None
    raw = m.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def extract_mf_server_side(html: str) -> dict[str, Any] | None:
    data = extract_next_data_json(html)
    if not data:
        return None
    props = data.get("props") or {}
    page = props.get("pageProps") or {}
    ms = page.get("mfServerSideData")
    if isinstance(ms, dict):
        return ms
    return None
