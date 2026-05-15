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

# Right-arrow send icon (matches app/ui/index.html send-btn SVG)
_SEND_ARROW_SVG = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
    "stroke='%230a0f0d' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E"
    "%3Cpath d='M5 12h14'/%3E%3Cpath d='M13 7l5 5-5 5'/%3E%3C/svg%3E"
)

_CUSTOM_CSS = f"""
<style>
/* Prevent title / New chat from sitting under Streamlit app chrome */
.stApp {{
  background-color: #0a0f0d;
}}
header[data-testid="stHeader"] {{
  background: rgba(10, 15, 13, 0.96) !important;
  border-bottom: 1px solid #24332e;
}}
[data-testid="stAppViewContainer"] [data-testid="stMain"] > div {{
  padding-top: 2.75rem !important;
}}
.block-container {{
  padding-top: 1.25rem !important;
  padding-bottom: 2rem !important;
  max-width: 920px;
}}
.block-container > div:first-child {{
  margin-top: 0 !important;
  padding-top: 0 !important;
}}

/* Page header — title + New chat */
.fundfacts-header {{
  padding-top: 0.5rem;
  margin-bottom: 0.75rem;
  overflow: visible;
}}
.fundfacts-header h1 {{
  color: #e8f0ed !important;
  font-weight: 800;
  letter-spacing: -0.02em;
  font-size: 1.75rem !important;
  line-height: 1.2 !important;
  margin: 0 0 0.35rem 0 !important;
  padding: 0 !important;
}}
.fundfacts-header [data-testid="stCaptionContainer"] p {{
  margin: 0 !important;
}}
.fundfacts-header [data-testid="column"]:last-child {{
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding-top: 0.15rem;
}}
.fundfacts-header [data-testid="column"]:last-child [data-testid="stVerticalBlock"] {{
  width: 100%;
}}

h1 {{
  color: #e8f0ed !important;
  font-weight: 800;
  letter-spacing: -0.02em;
  font-size: 1.75rem !important;
}}
div[data-testid="stCaptionContainer"] p,
.stCaption {{ color: #8fa39a !important; }}
div[data-testid="stChatMessage"] {{
  background: #161f1c;
  border: 1px solid #24332e;
  border-radius: 14px;
  padding: 0.35rem 0.75rem;
  margin-bottom: 0.5rem;
}}
div[data-testid="stChatMessage"] p {{ color: #e8f0ed; }}
div[data-baseweb="select"] > div {{
  background: #161f1c !important;
  border-color: #24332e !important;
}}
.stButton > button[kind="secondary"] {{
  border-color: rgba(165, 243, 208, 0.2);
  color: #a5f3d0;
  background: rgba(165, 243, 208, 0.08);
}}
.stButton > button[kind="secondary"]:hover {{
  border-color: #2d9c72;
  background: rgba(45, 156, 114, 0.2);
}}

/* Composer — matches app/ui/styles.css .input + .send-btn */
.fundfacts-composer {{ margin-top: 12px; }}
.fundfacts-composer [data-testid="stForm"] {{
  border: none !important;
  padding: 0 !important;
  background: transparent !important;
}}
.fundfacts-composer [data-testid="stForm"] > div {{ position: relative !important; }}
.fundfacts-composer [data-testid="stTextInput"] label {{ display: none !important; }}
.fundfacts-composer [data-testid="stTextInput"] input {{
  width: 100% !important;
  background: #161f1c !important;
  border: 1px solid #24332e !important;
  border-radius: 14px !important;
  color: #e8f0ed !important;
  padding: 16px 56px 16px 18px !important;
  font-size: 14px !important;
  min-height: 54px !important;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45) !important;
}}
.fundfacts-composer [data-testid="stTextInput"] input::placeholder {{ color: #5c6f68 !important; }}
.fundfacts-composer [data-testid="stTextInput"] input:focus {{
  border-color: #2d9c72 !important;
  box-shadow: 0 0 0 3px rgba(45, 156, 114, 0.18) !important;
}}
.fundfacts-composer [data-testid="stFormSubmitButton"] {{
  position: absolute !important;
  right: 8px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  z-index: 5 !important;
  width: 42px !important;
  min-width: 42px !important;
  margin: 0 !important;
  padding: 0 !important;
}}
.fundfacts-composer [data-testid="stFormSubmitButton"] button {{
  width: 42px !important;
  height: 42px !important;
  min-height: 42px !important;
  border-radius: 12px !important;
  background: #a5f3d0 !important;
  border: none !important;
  color: #0a0f0d !important;
  padding: 0 !important;
  display: grid !important;
  place-items: center !important;
  box-shadow: none !important;
}}
.fundfacts-composer [data-testid="stFormSubmitButton"] button:hover {{
  background: #bff7e0 !important;
  border: none !important;
  color: #0a0f0d !important;
}}
.fundfacts-composer [data-testid="stFormSubmitButton"] button:disabled {{
  opacity: 0.5 !important;
  cursor: not-allowed !important;
}}
.fundfacts-composer [data-testid="stFormSubmitButton"] button p,
.fundfacts-composer [data-testid="stFormSubmitButton"] button span,
.fundfacts-composer [data-testid="stFormSubmitButton"] button div {{
  display: none !important;
  font-size: 0 !important;
  line-height: 0 !important;
}}
.fundfacts-composer [data-testid="stFormSubmitButton"] button::after {{
  content: "" !important;
  display: block !important;
  width: 20px !important;
  height: 20px !important;
  background: url("{_SEND_ARROW_SVG}") center / contain no-repeat !important;
}}

.footer-note {{
  color: #5c6f68;
  font-size: 12px;
  margin: 14px 0 20px;
  text-align: center;
}}
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


def _render_composer() -> str | None:
    """Custom composer with mint send button matching the static UI design."""
    st.markdown('<div class="fundfacts-composer">', unsafe_allow_html=True)
    with st.form("fundfacts_composer", clear_on_submit=True, border=False):
        query = st.text_input(
            "Query",
            placeholder="Ask about expense ratios, exit loads, or fund returns...",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send", help="Send")
    st.markdown("</div>", unsafe_allow_html=True)
    if submitted and query and query.strip():
        return query.strip()
    return None


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

    st.markdown('<div class="fundfacts-header">', unsafe_allow_html=True)
    head_l, head_r = st.columns([5, 1], vertical_alignment="top")
    with head_l:
        st.title("Fundfacts FAQ RAG AI")
        st.caption("Factual mutual fund FAQ answers from the closed Groww corpus. Not financial advice.")
    with head_r:
        if st.button("New chat", type="secondary", use_container_width=True):
            _clear_chat()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

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

    prompt: str | None = None
    if st.session_state.pending_query:
        prompt = st.session_state.pending_query
        st.session_state.pending_query = ""
    else:
        prompt = _render_composer()

    if prompt:
        _ask(prompt.strip(), st.session_state.scheme_id)
        st.rerun()

    st.markdown(
        '<p class="footer-note">Fundfacts FAQ RAG AI provides factual mutual fund data based on '
        "historical disclosures. Not financial advice.</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
