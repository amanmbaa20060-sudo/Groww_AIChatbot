"""Phase 1.1 — manifest-driven HTTP fetch (docs/phase-wise-architecture.md §4.3)."""

from ingestion.phase1.subphase_1_1_fetch.runner import FetchResult, fetch_all, main

__all__ = ["FetchResult", "fetch_all", "main"]
