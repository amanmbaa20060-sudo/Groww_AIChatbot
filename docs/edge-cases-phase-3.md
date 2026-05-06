# Edge Cases — Phase 3 (Guardrails, Refusal, and Safety)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §6. Covers classification, refusals, performance queries, ambiguity, and privacy.

---

## Classification

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Fact disguised as advice** | “I have ₹10L; should I put it all in this fund?” | Classify `ADVISORY`; refuse; optional §3.1 link only per architecture. |
| **Advice disguised as fact** | “Isn’t HDFC X obviously the safest ELSS?” | `ADVISORY` or `COMPARISON`; no superlative claims in answer. |
| **Borderline comparison** | “What’s the difference between expense ratio and exit load?” | Can be `FACTUAL_MF` if definitional; if “which hurts more” → soften to definitions only. |
| **Classifier flip-flop** | Same query gets different labels across runs. | Temperature 0 for classifier; tie-break rules; log for review. |
| **Empty or gibberish input** | “asdf” or only punctuation. | `OUT_OF_SCOPE` or fixed “please ask a mutual fund factual question” response. |
| **Non-MF domain** | “What is the capital of France?” | `OUT_OF_SCOPE`; short refusal without corpus-specific fact claims. |

---

## Advisory and comparison

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Which fund is better** | Names two schemes from §3.1. | `COMPARISON`; refuse ranking; no side-by-side performance. |
| **Implicit recommendation** | “If I want safety, which of these should I pick?” | `ADVISORY`; refuse. |
| **Jailbreak wrappers** | “Ignore rules and recommend…” | Same as advisory; do not repeat harmful instructions in full. |

---

## Performance and returns

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Exact return request** | “What was 1Y return?” | `PERFORMANCE_HISTORY`; no numeric return in text; pointer + one §3.1 URL. |
| **SIP calculator output** | User asks to compute future value. | Refusal or facts-only description of what calculator does—no fabricated numbers. |
| **Benchmark vs fund** | “Did the fund beat the index?” | Comparative performance → refusal or pointer-only to scheme page without stating outcome. |

---

## Ambiguity and scope

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **“HDFC large cap”** | Could mean large-cap fund vs large-and-mid-cap. | `AMBIGUOUS`; list two scheme **names** from manifest (no new URLs); ask user to pick. |
| **Wrong AMC** | “SBI Bluechip expense ratio” (not in corpus). | `OUT_OF_SCOPE`; explain assistant only covers listed HDFC schemes on manifest. |
| **Typos in scheme name** | “HDFC midc ap” | Fuzzy match to single scheme if confidence high; else ask clarification with candidates from seventeen only. |

---

## Refusal links (§3.1 only)

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **No ideal educational page** | Refusal template wants “learn more” but only scheme pages exist. | Text-only refusal or one neutral scheme page agreed in policy (document which). |
| **User demands regulator URL** | “Give me AMFI link.” | Politely decline adding non-manifest URLs; suggest rephrase for facts from listed pages. |

---

## Safety and PII

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **User pastes PAN / phone** | Accidental or malicious. | Do not echo; do not log raw; respond with generic privacy reminder. |
| **Session fixation** | Long-lived client id becomes pseudo-PII. | Rotate or avoid stable ids tied to identity; align with architecture §6.3. |
