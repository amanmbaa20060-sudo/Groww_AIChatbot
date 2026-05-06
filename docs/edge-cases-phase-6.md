# Edge Cases — Phase 6 (Deployment and Operations)

Companion to [phase-wise-architecture.md](phase-wise-architecture.md) §9. Covers environments, secrets, corpus refresh, backup, and observability.

---

## Environments and configuration

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Dev uses prod API keys** | Cost leak or data policy breach. | Separate keys; `.env.example` without secrets; pre-deploy check. |
| **Wrong manifest path in prod** | App points at empty or stale YAML. | Startup validation: exactly 17 URLs, all HTTPS, all known paths. |
| **Feature flag drift** | Staging enables experimental retrieval; prod assumes old path. | Document flag matrix; infra as code where possible. |

---

## Secrets

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Key rotation** | Old key revoked mid-day. | Dual-key window; health check on embedding/LLM before traffic shift. |
| **Secret in log** | Crash dump prints env. | Redact known key patterns in logging config. |

---

## Corpus refresh and indexing

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Scheduled job overlap** | Two index builds run concurrently. | Mutex or leader election; single writer to vector store path. |
| **Disk full mid-index** | Partial write corrupts index. | Atomic swap: build to temp dir, verify, then rename. |
| **Groww global outage** | All fetches fail. | Preserve last good index; surface degraded mode banner in UI if product agrees. |

---

## Backup and recovery

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **Index lost, raw cache lost** | Only manifest remains. | Rebuild from manifest is full recovery path; document RTO as “re-ingest duration”. |
| **Restore old index with new code** | Schema mismatch. | Version index schema; migration script or full rebuild. |

---

## Observability

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **High refusal rate spike** | Classifier regression or attack traffic. | Dashboard refusal rate + sample rate for labels; alert on anomaly. |
| **Latency without breakdown** | Cannot tell fetch vs LLM slowness. | Span timings: retrieve, generate, validate. |
| **PII in error traces** | User message attached to exception. | Scrub payloads in error reporting pipeline. |

---

## Fresh clone / onboarding

| Edge case | Description | Suggested handling |
|-----------|-------------|-------------------|
| **README steps miss index step** | App runs but empty retrieval. | README “quickstart” ends with verified sample query hitting non-empty context. |
| **Platform-specific paths** | Windows vs Linux paths in docs. | Use neutral `path/to` or document both. |
