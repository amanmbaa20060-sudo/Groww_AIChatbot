"""
Groq Chat Completions client (OpenAI-compatible) using stdlib urllib.

Endpoint: https://api.groq.com/openai/v1/chat/completions
Auth: GROQ_API_KEY env var
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_DEFAULT_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _groq_chat_url() -> str:
    return (os.getenv("LLM_BASE_URL") or _DEFAULT_GROQ_URL).strip()


class GroqError(RuntimeError):
    pass


@dataclass(frozen=True)
class GroqChatResult:
    text: str
    raw: dict[str, Any]


def groq_chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str,
    temperature: float = 0.0,
    max_tokens: int = 250,
    timeout_s: float = 30.0,
) -> GroqChatResult:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise GroqError("Missing GROQ_API_KEY environment variable.")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        _groq_chat_url(),
        method="POST",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GrowwRAGChatbot/1.0",
        },
    )
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
    except HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        raise GroqError(f"Groq HTTPError {e.code}: {detail}") from e
    except URLError as e:
        raise GroqError(f"Groq URLError: {e}") from e

    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise GroqError("Groq response was not valid JSON.") from e

    try:
        text = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise GroqError(f"Unexpected Groq response shape: {data!r}") from e

    if not isinstance(text, str):
        raise GroqError("Groq message content was not a string.")

    return GroqChatResult(text=text.strip(), raw=data)

