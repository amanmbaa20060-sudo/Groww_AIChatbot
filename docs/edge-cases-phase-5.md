# Edge Cases — Phase 5 (Evaluation, Monitoring, and Limitations)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §8. Covers golden sets, metrics, regression, and honest limitation reporting.

---

## Golden set design

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Stale gold answers** | Page content changes; expected TER wrong. | Version gold set with `effective_as_of` date; refresh after each corpus rebuild. |
| **Multiple valid citations** | Two §3.1 pages could support same fact. | Gold specifies **expected** URL (primary scheme page) or allow small allowed set. |
| **Subjective “correct”** | Wording differs but fact same. | Use structured checks (numeric tolerance, keyword must-include) plus human spot. |
| **Tiny gold set** | Overfits to 5 questions. | Cover all seventeen URLs at least once across the suite; rotate additions. |

---

## Retrieval metrics

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Hit @k but wrong section** | Correct URL chunk but wrong table row. | Add span-level or field-level labels in gold; or human eval slice. |
| **Metric gaming** | Raise k until hit rate looks good. | Report @k with fixed k from architecture; separate wrong-scheme rate. |

---

## Generation metrics

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Valid URL, wrong fact** | Hallucinated number with real link. | Numeric extraction compare to gold or retrieved source; LLM-as-judge only as secondary signal. |
| **Sentence boundary bugs** | “Dr. No. 5%” splits sentences wrong. | Use tokenizer-aware sentence split for metric. |

---

## Regression and corpus refresh

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Refresh without regen** | New HTML but old index. | CI gate: index build hash must match manifest + fetch batch id before release. |
| **Flaky regression** | LLM non-determinism fails CI. | Temperature 0, fixed seed where supported; allow small tolerance band after agreement. |

---

## Limitations documentation

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Under-documented failure** | Known PDF/table issue never written down. | Limitations doc must list corpus lock, parsing weaknesses, and language scope. |
| **Over-promising** | README claims “always accurate”. | Use “best effort” + pointer to limitations and source link requirement. |

---

## Monitoring (if logs exist)

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Logs contain user queries** | Privacy or retention risk. | Aggregate metrics only, or hash/truncate per policy. |
| **Alert fatigue** | Every 404 on fetch pages ops. | Alert on sustained failure rate, not single blip. |
