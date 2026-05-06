# Guardrails (Phase 3)

Query gate: `FACTUAL_MF`, `ADVISORY`, `COMPARISON`, `PERFORMANCE_HISTORY`, `OUT_OF_SCOPE`, `AMBIGUOUS`.

Links in refusals, if any, must remain within the manifest URLs only.

## Additional policy (this repo)

- If the query is **`PERSONAL_INFO`** (PAN/Aadhaar/OTP/bank/contact info) → refuse and **do not include any URL**.
- If the system cannot answer from retrieved chunks (**`UNKNOWN`**) → respond with **no URL**.

## Groq integration (optional)

Phase 3 can optionally use **Groq** as an *answer generator* for factual queries (still grounded to retrieved snippets).

- Enable by setting `GROQ_API_KEY` and passing `--use-groq` to `python -m app.guardrails.cli`.
- The code enforces safety by attaching the single citation URL + footer **outside** the LLM output, and it never uses Groq for `PERSONAL_INFO` / `UNKNOWN` / `OUT_OF_SCOPE`.

See `docs/phase-wise-architecture.md` §6 and `docs/edge-cases-phase-3.md`.
