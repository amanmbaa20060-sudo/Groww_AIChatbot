"""
Compatibility entry point for Phase 1.1.

Prefer: python -m ingestion.phase1.subphase_1_1_fetch
"""

from ingestion.phase1.subphase_1_1_fetch.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
