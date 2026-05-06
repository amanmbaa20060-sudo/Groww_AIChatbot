"""Compatibility: Phase 1.5 index lives in ingestion.phase1.subphase_1_5_index."""

from ingestion.phase1.subphase_1_5_index.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
