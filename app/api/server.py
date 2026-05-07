"""
Minimal backend HTTP API for the Phase 4 UI.

Uses stdlib `http.server` (no extra dependencies).

POST /query
Request JSON:
  {
    "query": "string",
    "scheme_ids": ["optional", "scheme_id", "..."],
    "use_groq": false,
    "groq_model": "llama-3.1-8b-instant"
  }

Default use_groq is false (verbatim grounded lines). Set USE_GROQ_DEFAULT=1 to default true when GROQ_API_KEY is set.

Response JSON:
  {
    "label": "FACTUAL_MF|ADVISORY|...|UNKNOWN",
    "answer_text": "string",
    "citation_url": "string|null",
    "last_updated_from_sources_utc": "YYYY-MM-DD|null"
  }

Policy:
- If label is PERSONAL_INFO or UNKNOWN or OUT_OF_SCOPE or AMBIGUOUS → citation_url MUST be null.
"""

from __future__ import annotations

import json
import os
import re
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from app.guardrails.phase3 import QueryLabel, run_phase3_structured
from app.corpus.manifest import allowlisted_schemes


_SCHEME_TOKEN_STOP = frozenset({"hdfc", "fund", "direct", "growth", "plan", "of", "and", "the"})


def _infer_scheme_filter_from_query(*, query: str, chunks_root: Path) -> set[str] | None:
    """
    If the client doesn't pass scheme_ids, infer the most likely scheme_id from the question.
    This prevents cross-scheme leakage (wrong facts + wrong citation URL) for scheme-specific questions.
    """
    q = (query or "").lower()
    q_tokens = set(re.findall(r"[a-z0-9]+", q))
    if not q_tokens:
        return None

    best_score = 0
    best: list[str] = []
    try:
        scheme_dirs = [p for p in chunks_root.iterdir() if p.is_dir()]
    except Exception:
        return None

    for p in scheme_dirs:
        sid = p.name
        parts = [t for t in re.findall(r"[a-z0-9]+", sid.lower()) if t and t not in _SCHEME_TOKEN_STOP]
        if not parts:
            continue
        score = sum(1 for t in parts if t in q_tokens)
        if score > best_score:
            best_score = score
            best = [sid]
        elif score == best_score and score > 0:
            best.append(sid)

    # Require at least 2 matching tokens to avoid accidental matches.
    if best_score >= 2 and best:
        return {best[0]}
    return None


def _load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.is_file():
        return
    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not k:
            continue
        # Allow .env to fill missing OR empty env vars.
        if (k not in os.environ) or (os.environ.get(k, "").strip() == ""):
            os.environ[k] = v


def _groq_api_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def _default_use_groq() -> bool:
    # Factual answers use verbatim corpus lines by default; Groq can rephrase and introduce errors.
    # Opt in per request with `"use_groq": true` or set USE_GROQ_DEFAULT=1 in the environment.
    v = (os.getenv("USE_GROQ_DEFAULT") or "").strip().lower()
    if v in {"1", "true", "yes", "on"}:
        return _groq_api_configured()
    return False


def _default_groq_model() -> str:
    return str(os.getenv("GROQ_MODEL") or "llama-3.1-8b-instant")


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "GrowwRAGPhase4Backend/0.2"

    def _is_data_ready(self) -> bool:
        chunks_root = Path("data/chunks")
        if not chunks_root.exists():
            return False
        try:
            return next(chunks_root.rglob("chunks.jsonl"), None) is not None
        except Exception:
            return False

    def _text(self, code: int, text: str, *, content_type: str = "text/plain; charset=utf-8") -> None:
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, file_path: Path) -> None:
        if not file_path.is_file():
            self.send_response(404)
            self.end_headers()
            return
        content = file_path.read_bytes()
        ctype, _ = mimetypes.guess_type(str(file_path))
        if not ctype:
            ctype = "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json(self, code: int, obj: dict[str, Any]) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        # Basic CORS for local UI dev
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        # GET routes:
        # - /health     -> JSON status
        # - /schemes    -> JSON allowlisted schemes (Phase 0)
        # - /           -> app/ui/index.html
        # - /styles.css -> app/ui/styles.css
        # - /app.js     -> app/ui/app.js
        # - /ui/<file>  -> app/ui/<file>
        path = self.path.split("?", 1)[0]
        if path == "/health":
            return self._json(
                200,
                {
                    "ok": True,
                    "data_ready": self._is_data_ready(),
                    "llm_provider": "groq",
                    "groq_configured": _groq_api_configured(),
                    "groq_default_on": _default_use_groq(),
                    "groq_model_default": _default_groq_model(),
                },
            )
        if path == "/schemes":
            # UI helper for Phase 4: list schemes for selection; no secrets.
            return self._json(
                200,
                {
                    "schemes": allowlisted_schemes(),
                },
            )
        if path == "/" or path == "":
            return self._serve_static(Path("app/ui/index.html"))
        if path in {"/styles.css", "/app.js"}:
            return self._serve_static(Path("app/ui") / path.lstrip("/"))
        if path.startswith("/ui/"):
            rel = path[len("/ui/") :]
            # prevent path traversal
            if ".." in rel or rel.startswith(("/", "\\")):
                self.send_response(400)
                self.end_headers()
                return
            return self._serve_static(Path("app/ui") / rel)

        if path == "/query":
            return self._text(405, "Use POST /query\n")

        self._text(404, "Not found\n")

    def do_HEAD(self) -> None:  # noqa: N802
        # Provide basic HEAD support for browsers/health checks.
        path = self.path.split("?", 1)[0]
        if path == "/health":
            data = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return
        if path == "/" or path == "":
            file_path = Path("app/ui/index.html")
            if not file_path.is_file():
                self.send_response(404)
                self.end_headers()
                return
            ctype, _ = mimetypes.guess_type(str(file_path))
            if not ctype:
                ctype = "text/html; charset=utf-8"
            size = file_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return
        if path in {"/styles.css", "/app.js"}:
            file_path = Path("app/ui") / path.lstrip("/")
            if not file_path.is_file():
                self.send_response(404)
                self.end_headers()
                return
            ctype, _ = mimetypes.guess_type(str(file_path))
            if not ctype:
                ctype = "application/octet-stream"
            size = file_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return
        if path.startswith("/ui/"):
            rel = path[len("/ui/") :]
            if ".." in rel or rel.startswith(("/", "\\")):
                self.send_response(400)
                self.end_headers()
                return
            file_path = Path("app/ui") / rel
            if not file_path.is_file():
                self.send_response(404)
                self.end_headers()
                return
            ctype, _ = mimetypes.guess_type(str(file_path))
            if not ctype:
                ctype = "application/octet-stream"
            size = file_path.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.end_headers()
            return

        if path == "/query":
            self.send_response(405)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/query":
            self._json(404, {"error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"error": "invalid_content_length"})
            return

        body = self.rfile.read(max(0, length))
        try:
            req = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid_json"})
            return

        query = str(req.get("query") or "").strip()
        if not query:
            self._json(400, {"error": "missing_query"})
            return

        scheme_ids = req.get("scheme_ids")
        scheme_filter: set[str] | None = None
        if isinstance(scheme_ids, list):
            scheme_filter = {str(x) for x in scheme_ids if str(x).strip()}

        # Default to Groq when GROQ_API_KEY is present, unless explicitly overridden.
        if "use_groq" in req:
            use_groq = bool(req.get("use_groq"))
        else:
            use_groq = _default_use_groq()
        groq_model = str(req.get("groq_model") or _default_groq_model())

        chunks_root = Path("data/chunks")
        latest_batch = Path("data/registry/latest_batch.json")

        if scheme_filter is None:
            scheme_filter = _infer_scheme_filter_from_query(query=query, chunks_root=chunks_root)

        r = run_phase3_structured(
            query=query,
            chunks_root=chunks_root,
            registry_latest_path=latest_batch,
            scheme_filter=scheme_filter,
            use_groq=use_groq,
            groq_model=groq_model,
        )

        citation_url = r.citation_url
        last = r.last_updated_utc_date

        # Enforce no-URL rule for sensitive/unknown/clarification
        if r.label in {QueryLabel.PERSONAL_INFO, QueryLabel.UNKNOWN, QueryLabel.OUT_OF_SCOPE, QueryLabel.AMBIGUOUS}:
            citation_url = None

        self._json(
            200,
            {
                "label": str(r.label.value),
                "answer_text": r.answer_text,
                "citation_url": citation_url,
                "last_updated_from_sources_utc": last if citation_url else None,
                "llm_used": bool(r.llm_used),
                "llm_error": r.llm_error if not r.llm_used else None,
                "groq_model": groq_model if use_groq else None,
            },
        )


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    _load_dotenv(Path(".env"))
    if port is None:
        # Prefer env PORT if provided; otherwise pick a high default to avoid Windows restrictions.
        try:
            port = int(os.getenv("PORT", "8787"))
        except ValueError:
            port = 8787
    httpd = ThreadingHTTPServer((host, int(port)), ApiHandler)
    print(f"Serving on http://{host}:{int(port)} (POST /query)", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    serve()

