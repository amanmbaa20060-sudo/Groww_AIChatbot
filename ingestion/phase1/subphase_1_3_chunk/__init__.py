"""Phase 1.3 — chunking."""

from ingestion.phase1.subphase_1_3_chunk.chunker import chunk_normalized_text
from ingestion.phase1.subphase_1_3_chunk.runner import main, run_chunk

__all__ = ["chunk_normalized_text", "main", "run_chunk"]
