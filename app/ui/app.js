const backendUrl = (() => {
  const u = new URL(location.href);
  if (u.port === "5173") u.port = "8787";
  return `${u.protocol}//${u.hostname}${u.port ? `:${u.port}` : ""}`;
})();

const ICONS = {
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 14a4 4 0 0 1 0-5.7l1.3-1.3a4 4 0 0 1 5.7 5.7l-1 1"/><path d="M14 10a4 4 0 0 1 0 5.7l-1.3 1.3a4 4 0 0 1-5.7-5.7l1-1"/></svg>`,
};

function el(id) {
  return document.getElementById(id);
}

function highlightAnswer(text) {
  const escaped = String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped.replace(
    /\b(HDFC[\w\s]+(?:Fund|Growth|Plan)[\w\s]*|\d[\d.,]*)/g,
    "<strong class='highlight'>$1</strong>"
  );
}

function buildMetaHtml(data) {
  const cite = data.citation_url;
  const last = data.last_updated_from_sources_utc;
  const llmErr = data.llm_error;

  let html = "";

  if (cite) {
    const safe = String(cite);
    html += `<span class="meta-item">${ICONS.link}<a href="${safe}" target="_blank" rel="noreferrer">Source link</a></span>`;
  }

  if (last) {
    html += `<span class="meta-item"><span>Updated: ${last}</span></span>`;
  }

  if (llmErr) {
    html += `<span class="meta-item error"><span>${String(llmErr)}</span></span>`;
  }

  return html || null;
}

function appendMessage({ role, text, metaHtml }) {
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}`;

  if (role === "user") {
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
  } else {
    const avatar = document.createElement("div");
    avatar.className = "bot-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "🤖";

    const card = document.createElement("div");
    card.className = "assistant-card";

    const body = document.createElement("div");
    body.className = "assistant-text";
    body.innerHTML = highlightAnswer(text);
    card.appendChild(body);

    if (metaHtml) {
      const meta = document.createElement("div");
      meta.className = "meta-row";
      meta.innerHTML = metaHtml;
      card.appendChild(meta);
    }

    wrap.appendChild(avatar);
    wrap.appendChild(card);
  }

  el("messages").appendChild(wrap);
  el("messages").scrollTop = el("messages").scrollHeight;
}

async function submitQuery(q) {
  const sendBtn = el("sendBtn");
  sendBtn.disabled = true;

  appendMessage({ role: "user", text: q });

  const schemeId = (el("schemeSelect") && el("schemeSelect").value) || "";
  const body = { query: q };
  if (schemeId) body.scheme_ids = [schemeId];

  try {
    const resp = await fetch(`${backendUrl}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await resp.json();
    appendMessage({
      role: "assistant",
      text: data.answer_text || "No response.",
      metaHtml: buildMetaHtml(data),
    });
  } catch (e) {
    appendMessage({
      role: "assistant",
      text: "Request failed. Is the backend running?",
      metaHtml: null,
    });
  } finally {
    sendBtn.disabled = false;
  }
}

function wireExamples() {
  el("examples").addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-q]");
    if (!btn) return;
    el("query").value = btn.getAttribute("data-q");
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

async function loadSchemes() {
  const sel = el("schemeSelect");
  if (!sel) return;
  try {
    const resp = await fetch(`${backendUrl}/schemes`);
    const data = await resp.json();
    for (const s of (data.schemes || [])) {
      if (!s?.scheme_id || !s?.display_name) continue;
      const opt = document.createElement("option");
      opt.value = String(s.scheme_id);
      opt.textContent = String(s.display_name);
      sel.appendChild(opt);
    }
  } catch (e) {
    // keep default option
  }
}

function init() {
  el("backendUrl").textContent = backendUrl;
  wireExamples();
  wireComposer();
  loadSchemes();
}

init();
