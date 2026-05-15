const backendUrl = (() => {
  const u = new URL(location.href);
  if (u.port === "5173") u.port = "8787";
  return `${u.protocol}//${u.hostname}${u.port ? `:${u.port}` : ""}`;
})();

const ICONS = {
  link: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 14a4 4 0 0 1 0-5.7l1.3-1.3a4 4 0 0 1 5.7 5.7l-1 1"/><path d="M14 10a4 4 0 0 1 0 5.7l-1.3 1.3a4 4 0 0 1-5.7-5.7l1-1"/></svg>`,
  calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 11h18"/></svg>`,
};

const ADVISORY_SUGGESTIONS = [
  { label: "Expense ratio", q: "What is the expense ratio?" },
  { label: "Exit load", q: "What is the exit load?" },
  { label: "Benchmark", q: "What is the benchmark?" },
];

function el(id) {
  return document.getElementById(id);
}

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function setChatMode(active) {
  document.querySelector(".page")?.classList.toggle("has-chat", active);
}

function highlightAnswer(text) {
  const escaped = String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  return escaped
    .replace(/\b(\d[\d.,]*)\b/g, (m) => `<span class="value-pill">${m}</span>`)
    .replace(
      /\b(HDFC[\w\s]+(?:Fund|Growth|Plan)[\w\s]*)/gi,
      "<strong class='highlight'>$1</strong>"
    );
}

function labelHeading(label) {
  if (label === "FACTUAL_MF") return "Factual analysis";
  if (label === "ADVISORY" || label === "COMPARISON") return "Compliance notice";
  if (label === "UNKNOWN") return "Not found";
  return null;
}

function buildMetaHtml(data) {
  const cite = data.citation_url;
  const last = data.last_updated_from_sources_utc;
  const llmErr = data.llm_error;

  let html = "";

  if (cite) {
    const safe = String(cite);
    const short = safe.replace(/^https?:\/\//, "");
    html += `<span class="meta-item">${ICONS.link}<a href="${safe}" target="_blank" rel="noreferrer">${short}</a></span>`;
  }

  if (last) {
    html += `<span class="meta-item">${ICONS.calendar}<span>Updated: ${last}</span></span>`;
  }

  if (llmErr) {
    html += `<span class="meta-item error"><span>${String(llmErr)}</span></span>`;
  }

  return html || null;
}

function appendAdvisorySuggestions(card) {
  const block = document.createElement("div");
  block.className = "suggested-in-card";
  const title = document.createElement("div");
  title.className = "suggested-in-card-title";
  title.textContent = "Suggested factual queries";
  block.appendChild(title);
  for (const s of ADVISORY_SUGGESTIONS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.setAttribute("data-q", s.q);
    btn.textContent = s.label;
    block.appendChild(btn);
  }
  card.appendChild(block);
}

function appendUserMessage(text) {
  const wrap = document.createElement("div");
  wrap.className = "msg user";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  const time = document.createElement("span");
  time.className = "msg-time";
  time.textContent = `You • ${formatTime()}`;
  wrap.appendChild(bubble);
  wrap.appendChild(time);
  el("messages").appendChild(wrap);
}

function appendAssistantMessage({ text, metaHtml, label, showSuggestions }) {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";

  const avatar = document.createElement("div");
  avatar.className = "bot-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "🤖";

  const card = document.createElement("div");
  card.className = "assistant-card";

  const heading = labelHeading(label);
  if (heading) {
    const lbl = document.createElement("div");
    lbl.className = "assistant-label";
    lbl.textContent = heading;
    card.appendChild(lbl);
  }

  const body = document.createElement("div");
  body.className = "assistant-text";
  if (label === "FACTUAL_MF") {
    body.innerHTML = highlightAnswer(text);
  } else {
    body.classList.add("compact");
    body.textContent = text;
  }
  card.appendChild(body);

  if (showSuggestions) {
    appendAdvisorySuggestions(card);
  }

  if (metaHtml) {
    const meta = document.createElement("div");
    meta.className = "meta-row";
    meta.innerHTML = metaHtml;
    card.appendChild(meta);
  }

  wrap.appendChild(avatar);
  wrap.appendChild(card);
  el("messages").appendChild(wrap);
  scrollMessages();
}

function appendLoadingMessage() {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant loading";
  wrap.id = "loading-msg";

  const avatar = document.createElement("div");
  avatar.className = "bot-avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "🤖";

  const card = document.createElement("div");
  card.className = "assistant-card";

  const lbl = document.createElement("div");
  lbl.className = "assistant-label";
  lbl.textContent = "Assistant is typing";

  const skel = document.createElement("div");
  skel.className = "skeleton-lines";
  for (let i = 0; i < 3; i++) {
    const line = document.createElement("div");
    line.className = "skeleton-line";
    skel.appendChild(line);
  }

  const status = document.createElement("div");
  status.className = "loading-status";
  status.innerHTML =
    "<span>Querying scheme documents…</span><span class=\"active\">RAG engine active</span>";

  card.appendChild(lbl);
  card.appendChild(skel);
  card.appendChild(status);
  wrap.appendChild(avatar);
  wrap.appendChild(card);
  el("messages").appendChild(wrap);
  scrollMessages();
}

function removeLoadingMessage() {
  document.getElementById("loading-msg")?.remove();
}

function scrollMessages() {
  const box = el("messages");
  box.scrollTop = box.scrollHeight;
}

function wireSuggestionClicks(root) {
  root?.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-q]");
    if (!btn) return;
    el("query").value = btn.getAttribute("data-q");
    el("query").focus();
  });
}

async function submitQuery(q) {
  const sendBtn = el("sendBtn");
  const input = el("query");
  sendBtn.disabled = true;
  sendBtn.classList.add("processing");
  input.disabled = true;

  setChatMode(true);
  appendUserMessage(q);
  appendLoadingMessage();

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
    removeLoadingMessage();

    const label = data.label || "FACTUAL_MF";
    const isAdvisory = label === "ADVISORY" || label === "COMPARISON";

    appendAssistantMessage({
      text: data.answer_text || "No response.",
      metaHtml: buildMetaHtml(data),
      label,
      showSuggestions: isAdvisory,
    });
  } catch {
    removeLoadingMessage();
    appendAssistantMessage({
      text: "Request failed. Is the backend running?",
      metaHtml: null,
      label: "UNKNOWN",
      showSuggestions: false,
    });
  } finally {
    sendBtn.disabled = false;
    sendBtn.classList.remove("processing");
    input.disabled = false;
  }
}

function wireExamples() {
  wireSuggestionClicks(el("examples"));
  wireSuggestionClicks(el("suggestedQueries"));
  el("messages")?.addEventListener("click", (ev) => {
    const btn = ev.target.closest(".suggested-in-card button[data-q]");
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
    for (const s of data.schemes || []) {
      if (!s?.scheme_id || !s?.display_name) continue;
      const opt = document.createElement("option");
      opt.value = String(s.scheme_id);
      opt.textContent = String(s.display_name);
      sel.appendChild(opt);
    }
  } catch {
    // keep default option
  }
}

function init() {
  wireExamples();
  wireComposer();
  loadSchemes();
}

init();

