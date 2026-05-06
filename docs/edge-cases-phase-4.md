# Edge Cases — Phase 4 (Minimal User Interface)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §7. Covers welcome, examples, disclaimer, rendering, and privacy on the client.

---

## Layout and compliance copy

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Disclaimer scrolled away** | User scrolls chat; disclaimer not visible. | Sticky footer/bar, or repeat disclaimer on first message of each session. |
| **Small viewports** | Mobile: disclaimer wraps below fold. | Minimum height reserved for disclaimer + input. |
| **Example question is advisory** | Accidental copy: “Should I invest in ELSS?” | QA all three examples; must be purely factual phrasing. |

---

## Message rendering

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Multiple URLs in payload** | API bug returns two links. | UI shows first §3.1 link only or rejects render until fixed—never render non-§3.1 URLs. |
| **Link opens in-app browser** | User loses chat context. | `target="_blank"` + `rel="noopener noreferrer"` per security baseline. |
| **Very long “three sentences”** | No hard character limit in API. | Optional UI clamp with “see source” emphasis on link. |
| **Markdown XSS** | Assistant returns raw HTML/script. | Sanitize markdown subset; no raw HTML from model in DOM. |

---

## Input and interaction

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Extremely long user paste** | Whole factsheet pasted into chat. | Truncate server-side with clear error; avoid token abuse. |
| **Rapid-fire sends** | Double-click submit duplicates requests. | Disable button until response; dedupe in-flight by client id. |
| **Offline / flaky network** | Request fails after timeout. | Retry once with backoff; show non-alarming error. |

---

## Privacy (UI layer)

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Analytics on prompts** | Third-party script captures query text. | Disable or hash; align with “no PII” and product policy. |
| **URL prefetch** | Browser prefetches citation links and leaks behavior. | Acceptable for public pages; document if enterprise policy differs. |

---

## Accessibility and i18n

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Screen reader on disclaimer** | Treated as decorative text. | Use semantic landmark + `aria` where appropriate. |
| **RTL / future locale** | Layout breaks if Hindi added later. | English-only for MVP; document constraint. |
