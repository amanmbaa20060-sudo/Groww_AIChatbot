# Edge Cases — Phase 1 (Ingestion, Normalization, and Indexing)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §4. Covers fetch, parse, chunk, embed, and metadata for the **fixed seventeen Groww URLs** only.

---

## Fetcher

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **429 / rate limit** | Groww throttles automated requests. | Backoff, jitter, reduce concurrency; respect `Retry-After`; log URL and timestamp. |
| **403 / bot block** | WAF or geo block. | Identify with documented UA; if persistent, stop and escalate (do not add non-manifest proxies that imply new sources). |
| **Timeout / partial body** | Connection drops mid-response. | Retry with idempotency; do not index partial HTML as complete. |
| **Redirect chain** | 301 → 302 → final URL. | After redirects, final URL **must** match a §3.1 URL exactly or discard. |
| **Empty or minimal body** | Page returns shell with client-rendered content only. | Detect low text ratio; flag for human review; do not silently index empty chunks. |
| **Soft 404** | HTTP 200 but “page not found” content. | Heuristic or checksum vs known good template; block index until resolved. |

---

## Parser and normalizer

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Boilerplate dominates** | Nav, footer, and related funds flood extracted text. | Aggressive stripping; verify key sections (expense ratio, exit load) still present post-strip. |
| **Duplicate sections** | Same exit-load block repeated (historical rows on page). | Dedupe by normalized text hash or section id; prefer latest effective row if dates visible. |
| **Tables mangled** | HTML `<table>` flattened so numbers lose column alignment. | Table-aware extraction or structured scrape for critical fields; spot-check vs rendered page. |
| **Unicode / rupee** | `₹`, thin spaces, special dashes break search. | Normalize NFC, currency symbols, hyphen variants. |
| **Embedded PDF** | SID link points off-manifest PDF. | Do **not** fetch off-manifest PDFs; index only visible HTML text on the §3.1 page. |

---

## Chunker and embeddings

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Chunk splits mid-fact** | Expense ratio split across two chunks (“0.” / “21%”). | Prefer heading-aware chunks; overlap sufficient to preserve short fact lines. |
| **Wrong `scheme_ids`** | Chunk tagged with multiple schemes because of “also manages” sidebar. | Tag primary page scheme first; optionally secondary mentions with lower weight or exclude from RAG. |
| **Very short page region** | Chunk below minimum tokens is all noise. | Merge with adjacent or drop if no substantive tokens. |
| **Embedding API failure** | Transient error mid-batch. | Retry failed IDs only; do not mark URL complete until all chunks embedded. |

---

## Vector store and metadata

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Re-run partial upsert** | Old vectors remain for replaced chunks. | Delete by `source_url` + version then insert; or transactional replace per URL. |
| **ETag missing** | Server omits caching headers. | Rely on content hash for change detection; full refetch on schedule. |
| **Clock skew** | `last_fetch` vs user footer date inconsistent. | Use server UTC; document in Phase 0 policy. |

---

## Exit criteria stress

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **One URL always fails** | Single scheme page broken for days. | Operational flag: exclude from answerable set or show “source temporarily unavailable” without inventing facts. |
