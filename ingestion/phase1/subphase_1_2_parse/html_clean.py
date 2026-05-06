"""Strip boilerplate from HTML and extract visible text (DOM-aware via BeautifulSoup)."""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup


def extract_visible_text(html: str, *, max_chars: int = 50_000) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    body = soup.body
    if not body:
        text = soup.get_text(separator="\n")
    else:
        text = body.get_text(separator="\n")
    lines = []
    for line in text.splitlines():
        s = unicodedata.normalize("NFKC", line).strip()
        if len(s) < 2:
            continue
        # Drop obvious nav/footer noise (heuristic)
        if s.lower() in {"stocks", "mutual funds", "more", "download the app", "contact us"}:
            continue
        lines.append(s)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    if len(out) > max_chars:
        out = out[: max_chars - 20] + "\n...[truncated]..."
    return out.strip()
