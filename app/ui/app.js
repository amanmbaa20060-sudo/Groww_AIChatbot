const backendUrl = (() => {
  // If UI is served separately (e.g. :5173), talk to API on :8787.
  // If UI is served by the backend itself, same-origin works.
  const u = new URL(location.href);
  if (u.port === "5173") u.port = "8787";
  return `${u.protocol}//${u.hostname}${u.port ? `:${u.port}` : ""}`;
})();

function el(id) {
  return document.getElementById(id);
}

function appendMessage({ role, text, metaHtml }) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  wrap.appendChild(bubble);

  if (metaHtml) {
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = metaHtml;
    wrap.appendChild(meta);
  }

  el("messages").appendChild(wrap);
  el("messages").scrollTop = el("messages").scrollHeight;
}

async function submitQuery(q) {
  const sendBtn = el("sendBtn");
  sendBtn.disabled = true;

  appendMessage({ role: "user", text: q });

  const body = {
    query: q,
    use_groq: true,
  };

  try {
    const resp = await fetch(`${backendUrl}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await resp.json();
    const label = data.label || "UNKNOWN";
    const answerText = data.answer_text || "No response.";
    const cite = data.citation_url;
    const last = data.last_updated_from_sources_utc;

    let meta = `<b>${label}</b>`;
    if (data.llm_used) {
      meta += ` — <b>LLM</b>`;
    }
    if (cite) {
      const safeUrl = String(cite);
      meta += ` — Source: <a href="${safeUrl}" target="_blank" rel="noreferrer">${safeUrl}</a>`;
    }
    if (last) {
      meta += `<br/>Last updated from sources: <b>${last}</b>`;
    }

    appendMessage({ role: "assistant", text: answerText, metaHtml: meta });
  } catch (e) {
    appendMessage({ role: "assistant", text: "Request failed. Is the backend running?", metaHtml: null });
  } finally {
    sendBtn.disabled = false;
  }
}

function wireExamples() {
  el("examples").addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-q]");
    if (!btn) return;
    const q = btn.getAttribute("data-q");
    el("query").value = q;
    el("query").focus();
  });
}

function wireComposer() {
  el("composer").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const q = el("query").value.trim();
    if (!q) return;
    el("query").value = "";
    submitQuery(q);
  });
}

function init() {
  el("backendUrl").textContent = backendUrl;
  wireExamples();
  wireComposer();
  appendMessage({
    role: "assistant",
    text: "Ask a factual question about one of the 17 schemes (expense_ratio, exit_load, benchmark, fund_manager, etc.).",
    metaHtml: "<b>Facts-only.</b> No investment advice.",
  });
}

init();

