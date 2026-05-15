"""Fundfacts FAQ RAG AI — Streamlit frontend (calls the Phase 4 HTTP API)."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import streamlit as st

EXAMPLE_QUESTIONS = (
    ("Exit load", "What is the exit load?"),
    ("Expense ratio", "What is the expense ratio?"),
    ("Fund Manager", "Who is the fund manager?"),
    ("AUM", "What is the AUM?"),
)

ADVISORY_SUGGESTIONS = (
    ("Expense ratio", "What is the expense ratio?"),
    ("Exit load", "What is the exit load?"),
    ("Benchmark", "What is the benchmark?"),
)

_PLACEHOLDER_HOSTS = frozenset(
    {
        "your-render-backend.onrender.com",
        "localhost",
        "127.0.0.1",
    }
)

_CUSTOM_CSS = """
<style>
.block-container { padding-top: 1rem; max-width: 920px; }
h1 {
  color: #e8f0ed !important;
  font-weight: 800;
  letter-spacing: -0.02em;
  font-size: 1.75rem !important;
}
div[data-testid="stCaptionContainer"] p,
.stCaption { color: #8fa39a !important; }
div[data-testid="stChatMessage"] {
  background: #161f1c;
  border: 1px solid #24332e;
  border-radius: 14px;
  padding: 0.35rem 0.75rem;
  margin-bottom: 0.5rem;
}
div[data-testid="stChatMessage"] p { color: #e8f0ed; }
div[data-baseweb="select"] > div {
  background: #161f1c !important;
  border-color: #24332e !important;
}
.stButton > button[kind="secondary"] {
  border-color: rgba(165, 243, 208, 0.2);
  color: #a5f3d0;
  background: rgba(165, 243, 208, 0.08);
}
.stButton > button[kind="secondary"]:hover {
  border-color: #2d9c72;
  background: rgba(45, 156, 114, 0.2);
}
.footer-note {
  color: #5c6f68;
  font-size: 0.8rem;
  margin-top: 2rem;
  text-align: center;
}
</style>
"""


def _is_streamlit_cloud() -> bool:
    return os.getenv("STREAMLIT_RUNTIME_ENV", "").strip().lower() == "cloud"


def _read_backend_url_from_secrets() -> str:
    try:
        secret = st.secrets.get("RAG_BACKEND_URL")
        if secret:
            return str(secret).strip().rstrip("/")
    except Exception:
        pass
    return os.getenv("RAG_BACKEND_URL", "").strip().rstrip("/")


def _backend_url() -> str:
    url = _read_backend_url_from_secrets()
    if url:
        return url
    if _is_streamlit_cloud():
        return ""
    return "http://localhost:8787"


def _backend_url_issue(url: str) -> str | None:
    if not url:
        return (
            "Set `RAG_BACKEND_URL` in Streamlit Cloud → **Manage app → Settings → Secrets** "
            "to your Render backend URL, e.g. `https://groww-rag-backend.onrender.com` "
            "(use the exact URL from the Render dashboard)."
        )
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return f"`RAG_BACKEND_URL` is not a valid URL: `{url}`"
    if host in _PLACEHOLDER_HOSTS or "your-render-backend" in host:
        return (
            "Replace the placeholder backend host with your real Render service URL "
            f"(current value: `{url}`)."
        )
    if parsed.scheme not in {"http", "https"}:
        return f"`RAG_BACKEND_URL` must start with http:// or https:// (got `{url}`)."
    return None


def _http_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{_backend_url()}{path}"
    data = None
    headers = {"Accept": "application/json", "User-Agent": "FundfactsStreamlit/1.0"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _load_schemes(backend: str) -> list[dict[str, str]]:
    url = f"{backend.rstrip('/')}/schemes"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "FundfactsStreamlit/1.0"}, method="GET")
    with urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    rows = body.get("schemes") or []
    out: list[dict[str, str]] = []
    for row in rows:
        sid = str(row.get("scheme_id") or "").strip()
        name = str(row.get("display_name") or "").strip()
        if sid and name:
            out.append({"scheme_id": sid, "display_name": name})
    return sorted(out, key=lambda r: r["display_name"].lower())


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "scheme_id" not in st.session_state:
        st.session_state.scheme_id = ""
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = ""


def _clear_chat() -> None:
    st.session_state.messages = []
    st.session_state.pending_query = ""


def _render_meta(citation_url: str | None, last_updated: str | None) -> None:
    parts: list[str] = []
    if citation_url:
        parts.append(f"[Source link]({citation_url})")
    if last_updated:
        parts.append(f"Updated: {last_updated}")
    if parts:
        st.caption(" · ".join(parts))


def _render_advisory_suggestions() -> None:
    st.caption("Try a factual question instead:")
    cols = st.columns(len(ADVISORY_SUGGESTIONS))
    for col, (label, question) in zip(cols, ADVISORY_SUGGESTIONS):
        if col.button(label, key=f"adv_{label}", use_container_width=True):
            st.session_state.pending_query = question
            st.rerun()


def _ask(query: str, scheme_id: str) -> None:
    st.session_state.messages.append({"role": "user", "content": query})
    body: dict[str, Any] = {"query": query}
    if scheme_id:
        body["scheme_ids"] = [scheme_id]
    try:
        data = _http_json("POST", "/query", body)
        label = str(data.get("label") or "")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": data.get("answer_text") or "No response.",
                "label": label,
                "citation_url": data.get("citation_url"),
                "last_updated": data.get("last_updated_from_sources_utc"),
            }
        )
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Backend error ({e.code}): {detail}", "label": "ERROR"}
        )
    except URLError:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"Could not reach the API at `{_backend_url()}`. Is the backend running?",
                "label": "ERROR",
            }
        )
    except Exception as e:
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Request failed: {e}", "label": "ERROR"}
        )


def main() -> None:
    st.set_page_config(
        page_title="Fundfacts FAQ RAG AI",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    _init_state()
    backend = _backend_url()
    backend_issue = _backend_url_issue(backend)

    head_l, head_r = st.columns([5, 1])
    with head_l:
        st.title("Fundfacts FAQ RAG AI")
        st.caption("Factual mutual fund FAQ answers from the closed Groww corpus. Not financial advice.")
    with head_r:
        st.write("")
        if st.button("New chat", type="secondary", use_container_width=True):
            _clear_chat()
            st.rerun()

    if backend_issue:
        st.error(backend_issue)
        with st.expander("Streamlit Cloud secret (required)", expanded=True):
            st.code(
                'RAG_BACKEND_URL = "https://groww-rag-backend.onrender.com"',
                language="toml",
            )
        st.stop()

    with st.container(border=True):
        st.markdown("**Try an example**")
        try:
            schemes = _load_schemes(backend)
        except URLError as e:
            st.error(
                f"Cannot reach the backend at `{backend}`. "
                f"Check that the Render service is live and the URL is correct.\n\n`{e}`"
            )
            st.stop()
        except Exception as e:
            st.error(f"Failed to load schemes from `{backend}/schemes`: {e}")
            st.stop()

        scheme_options = {"Auto-detect from question": ""}
        scheme_options.update({s["display_name"]: s["scheme_id"] for s in schemes})
        labels = list(scheme_options.keys())
        current_label = next(
            (label for label, sid in scheme_options.items() if sid == st.session_state.scheme_id),
            "Auto-detect from question",
        )
        selected_label = st.selectbox(
            "Scheme",
            labels,
            index=labels.index(current_label) if current_label in labels else 0,
            label_visibility="collapsed",
        )
        st.session_state.scheme_id = scheme_options[selected_label]

        cols = st.columns(len(EXAMPLE_QUESTIONS))
        for col, (label, question) in zip(cols, EXAMPLE_QUESTIONS):
            if col.button(label, use_container_width=True):
                st.session_state.pending_query = question

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else None):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                _render_meta(msg.get("citation_url"), msg.get("last_updated"))
                label = msg.get("label") or ""
                if label in {"ADVISORY", "COMPARISON"}:
                    _render_advisory_suggestions()

    prompt = st.session_state.pending_query or st.chat_input(
        "Ask about expense ratios, exit loads, or fund returns..."
    )
    if st.session_state.pending_query:
        st.session_state.pending_query = ""

    if prompt:
        _ask(prompt.strip(), st.session_state.scheme_id)
        st.rerun()

    with st.expander("API connection", expanded=False):
        st.code(backend, language=None)
        if st.button("Check /health"):
            try:
                health = _http_json("GET", "/health")
                st.json(health)
            except Exception as e:
                st.error(str(e))

    st.markdown(
        '<p class="footer-note">Fundfacts FAQ RAG AI · Facts from Groww scheme pages only · Not investment advice</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
