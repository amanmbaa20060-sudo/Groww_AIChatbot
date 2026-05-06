"""Repository-root resolution for Phase 1 jobs (run from any CWD)."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return …/GrowwRAGChatbot_M2 (parent of `ingestion/`)."""
    # ingestion/phase1/common/paths.py -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]
