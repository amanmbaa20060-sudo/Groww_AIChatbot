# “Last updated from sources” policy (Phase 0)

Defines a single, consistent meaning for the user-facing footer required by the problem statement:

`Last updated from sources: <date>`

## Chosen rule (normative for this repo)

**Use the UTC calendar date of the ingestion batch** that produced the indexed snapshot backing the answer.

- Format: `YYYY-MM-DD` (UTC).
- The API or batch job sets this value at index build or query time from stored metadata (e.g. `ingestion_batch_date_utc` written when the vector index was last rebuilt), not from free-form model text.
- If the index has not yet been built (development), use the manifest validation date or a documented placeholder only in non-production environments.

## Rationale

- Groww HTML may not expose reliable `Last-Modified` for the full page.
- Crawl-time UTC is reproducible and matches operational reality (re-index cadence).

## Out of scope for Phase 0

- Wiring this field into the API response is Phase 2+; this document locks the **semantic** choice for product and eval consistency.
