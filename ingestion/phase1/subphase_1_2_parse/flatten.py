"""Turn mfServerSideData into readable plain text with section sentinels for chunking."""

from __future__ import annotations

import json
from typing import Any

# Very large / low-signal keys (keep brochure_link etc. as single line elsewhere if needed)
SKIP_KEYS: frozenset[str] = frozenset(
    {
        "nfo_image_url",
        "meta_image",
        "og_image",
        "twitter_image",
    }
)

MAX_LIST_ITEMS = 80
MAX_DEPTH = 8
MAX_STR_LEN = 2000


def _trim(s: str) -> str:
    s = s.strip()
    if len(s) > MAX_STR_LEN:
        return s[: MAX_STR_LEN - 3] + "..."
    return s


def walk(obj: Any, prefix: str, lines: list[str], depth: int) -> None:
    if depth > MAX_DEPTH:
        lines.append(f"{prefix}: <max_depth>")
        return
    if obj is None:
        return
    if isinstance(obj, bool):
        lines.append(f"{prefix}: {str(obj).lower()}")
        return
    if isinstance(obj, (int, float)):
        lines.append(f"{prefix}: {obj}")
        return
    if isinstance(obj, str):
        t = _trim(obj)
        if t:
            lines.append(f"{prefix}: {t}")
        return
    if isinstance(obj, list):
        for i, item in enumerate(obj[:MAX_LIST_ITEMS]):
            walk(item, f"{prefix}[{i}]", lines, depth + 1)
        if len(obj) > MAX_LIST_ITEMS:
            lines.append(f"{prefix}: <list truncated {len(obj) - MAX_LIST_ITEMS} more items>")
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            nk = f"{prefix}.{k}" if prefix else k
            walk(v, nk, lines, depth + 1)
        return
    lines.append(f"{prefix}: {_trim(json.dumps(obj, default=str))}")


def mf_server_side_to_text(ms: dict[str, Any]) -> str:
    lines: list[str] = []
    for top_key in sorted(ms.keys()):
        if top_key in SKIP_KEYS:
            continue
        lines.append(f"<<<SECTION:{top_key}>>>")
        walk(ms[top_key], top_key, lines, 0)
    text = "\n".join(lines)
    # Collapse excessive blank lines
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def dedupe_consecutive_lines(text: str) -> str:
    out: list[str] = []
    prev: str | None = None
    repeats = 0
    for line in text.splitlines():
        s = line.strip()
        if s == prev and s:
            repeats += 1
            if repeats >= 2:
                continue
        else:
            repeats = 0
        prev = s if s else None
        out.append(line)
    return "\n".join(out).strip()
