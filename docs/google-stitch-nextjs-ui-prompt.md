# Google Stitch UI Prompt (Next.js Frontend)

Copy the prompt below into **Google Stitch** to generate UI mockups / screen images for the Next.js frontend of this project.

---

## Prompt (copy from here)

Design a modern, production-ready **Next.js (App Router) web UI** for a **facts-only Mutual Fund FAQ chatbot** inspired by Groww’s product context (do **not** use Groww’s official logo or trademark assets).

### Product summary
- **Name:** Groww Mutual Fund FAQ Assistant (working title)
- **Purpose:** Answer **objective, verifiable** mutual fund questions from a **closed corpus of 17 HDFC scheme pages** on Groww.
- **Tone:** Trustworthy, compliant, concise — **not** salesy or advisory.
- **LLM:** Optional Groq-powered phrasing; answers must remain grounded and factual.

### Users
- Retail investors comparing HDFC mutual fund schemes
- Support/content teams handling repetitive factual MF queries

### Design direction
- **Theme:** Light, clean fintech UI
- **Background:** Soft off-white (`#f6f7fb`) with subtle purple/blue radial gradients
- **Accent:** Indigo/violet (`#635bff` / `#4f46e5`)
- **Cards:** White, rounded (12–14px), light border, soft shadow
- **Typography:** Modern sans-serif (Inter / system UI)
- **Layout:** Centered max-width ~980px, responsive for desktop + mobile
- **Accessibility:** High contrast text, clear focus states, readable 14–16px body

### Required screens (generate as separate mockups)
1. **Main chat screen (desktop)**
2. **Main chat screen (mobile)**
3. **Empty state** (before first question)
4. **Loading state** (message being sent)
5. **Assistant response state** (with metadata)
6. **Guardrail refusal state** (advice / personal info / unknown — no source link)

### Required UI components
Include these in the layouts:

**Header**
- Title: “Groww Mutual Fund FAQ Assistant”
- Subtitle: “Facts-only. Closed corpus (17 Groww scheme pages). No investment advice. LLM provider: Groq (optional).”

**Scheme selector card**
- Section title: “Try an example”
- Dropdown: “Scheme (optional)” with default option “Auto-detect from question”
- Example chips/buttons:
  - Exit load
  - Expense ratio
  - ELSS lock-in
  - NAV
  - Groww rating
  - Summarize fund

**Disclaimer block (prominent but subtle)**
- “Facts-only. No investment advice.”
- Privacy note: “Don’t share PAN, Aadhaar, OTP, bank details, phone, email, or transaction/portfolio details.”

**Chat panel**
- Scrollable message list
- User bubble: light purple tint
- Assistant bubble: neutral white/gray
- Composer: text input + “Send” button (disabled while loading)

**Assistant metadata row (below answer bubble)**
Show compact metadata chips/labels:
- Label badge: `FACTUAL_MF`, `ADVISORY`, `UNKNOWN`, etc.
- `LLM` badge when Groq is used
- Model name (e.g. `llama-3.1-8b-instant`)
- Source link (single citation URL) when allowed
- “Last updated from sources: YYYY-MM-DD”
- Optional small `LLM error` line in muted red when provider fails

### Sample content to render in mockups
Use realistic example text:

**User:** “What is the NAV of HDFC Defence Fund Direct Growth?”

**Assistant:** “As of May 6, 2026, the Net Asset Value (NAV) of HDFC Defence Fund Direct Growth is 28.004.”

**Metadata:** `FACTUAL_MF` · `LLM` · Model: `llama-3.1-8b-instant` · Source: `groww.in/mutual-funds/hdfc-defence-fund-direct-growth` · Last updated: `2026-05-07`

**User:** “Should I invest in HDFC Mid Cap?”

**Assistant:** “I can’t provide investment advice or comparisons. If you ask for a specific factual field (expense ratio, exit load, benchmark, etc.), I can answer from the indexed corpus.”

**Metadata:** `ADVISORY` · No source link

### Interaction details to visualize
- Clicking an example chip fills the input with a sample question
- Scheme dropdown narrows answers to one fund when selected
- Send button shows loading/disabled state during API call
- Source URL opens in new tab
- Mobile: stacked layout, sticky composer at bottom

### Next.js implementation hints (for visual alignment only)
Design should map cleanly to a Next.js App Router structure:
- `app/page.tsx` — main chat page
- `components/Header.tsx`
- `components/SchemeSelect.tsx`
- `components/ExampleChips.tsx`
- `components/ChatMessages.tsx`
- `components/ChatComposer.tsx`
- `components/ResponseMeta.tsx`
- `components/Disclaimer.tsx`

Use component-friendly spacing and reusable design tokens.

### Do NOT include
- Buy/Sell/Recommend buttons
- Portfolio dashboards
- Performance charts or return rankings
- Multiple citation links per answer
- Dark patterns or aggressive CTAs
- Official Groww branding assets

### Deliverables
Generate **high-fidelity UI mockups** (not code) for all required screens, consistent visual system, suitable as reference for building the Next.js frontend.

---

## Optional follow-up prompts for Stitch

Use these if you want more variations:

**Desktop component sheet**
> Create a Next.js UI component sheet for the Groww Mutual Fund FAQ Assistant: buttons, chips, input, select dropdown, chat bubbles, metadata badges, disclaimer card, and footer. Light fintech theme, accent #635bff.

**Mobile-first refinement**
> Redesign the mutual fund FAQ chatbot for mobile-first Next.js: sticky input bar, compact metadata, collapsible disclaimer, and thumb-friendly chips.

**Empty + error states**
> Add empty, loading, and error states for a facts-only mutual fund FAQ chatbot UI (Next.js). Include ADVISORY refusal with no URL and UNKNOWN response with no URL.
