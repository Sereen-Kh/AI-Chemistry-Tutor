"""Structured diagnostic logging for the RAG retrieval pipeline.

Every QA request is traced through the pipeline:
  original_query → normalized_query → detected_intent → rewritten_query
  → top_N_candidates → final_top_k → final_confidence

Uses Python logging at INFO level on the ``rag.diagnostics`` logger
so it can be filtered, shipped to a file, or suppressed independently.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field

logger = logging.getLogger("rag.diagnostics")


@dataclass
class CandidateInfo:
    """Summary of a single retrieved chunk for diagnostic output."""

    chunk_id: int
    page_number: int | None
    source_type: str
    content_type: str
    vector_score: float
    lexical_score: float
    hybrid_score: float
    snippet: str  # First 120 chars of content


@dataclass
class RetrievalDiagnostics:
    """Collects diagnostic data for a single RAG retrieval request."""

    original_query: str = ""
    normalized_query: str = ""
    detected_intent: str = "general"
    rewritten_query: str = ""
    query_terms: list[str] = field(default_factory=list)
    total_candidates_scanned: int = 0
    top_candidates: list[CandidateInfo] = field(default_factory=list)
    final_top_k: list[CandidateInfo] = field(default_factory=list)
    final_confidence: float = 0.0
    retrieval_time_ms: int = 0
    cache_hit: bool = False
    source_statuses_used: list[str] = field(default_factory=list)

    _start_time: float = field(default=0.0, repr=False)

    def start_timer(self) -> None:
        self._start_time = time.monotonic()

    def stop_timer(self) -> None:
        if self._start_time > 0:
            self.retrieval_time_ms = int((time.monotonic() - self._start_time) * 1000)

    def add_candidate(
        self,
        chunk_id: int,
        page_number: int | None,
        source_type: str,
        content_type: str,
        vector_score: float,
        lexical_score: float,
        hybrid_score: float,
        content: str,
    ) -> None:
        info = CandidateInfo(
            chunk_id=chunk_id,
            page_number=page_number,
            source_type=source_type,
            content_type=content_type,
            vector_score=round(vector_score, 4),
            lexical_score=round(lexical_score, 4),
            hybrid_score=round(hybrid_score, 4),
            snippet=content[:120].replace("\n", " "),
        )
        self.top_candidates.append(info)

    def set_final(self, final_chunks: list[CandidateInfo] | None = None) -> None:
        """Mark the final selected top-k from top_candidates."""
        if final_chunks is not None:
            self.final_top_k = final_chunks
        elif self.top_candidates:
            # Use the first top_k from sorted candidates
            self.final_top_k = self.top_candidates[:]

    def emit(self) -> None:
        """Emit the diagnostics as a structured JSON log line."""
        self.stop_timer()
        payload = {
            "event": "rag_retrieval",
            "original_query": self.original_query,
            "normalized_query": self.normalized_query,
            "detected_intent": self.detected_intent,
            "rewritten_query": self.rewritten_query,
            "query_terms": self.query_terms,
            "total_candidates_scanned": self.total_candidates_scanned,
            "top_candidates_count": len(self.top_candidates),
            "top_candidates": [asdict(c) for c in self.top_candidates[:10]],
            "final_top_k": [asdict(c) for c in self.final_top_k],
            "final_confidence": round(self.final_confidence, 4),
            "retrieval_time_ms": self.retrieval_time_ms,
            "cache_hit": self.cache_hit,
        }
        logger.info("RAG_DIAG %s", json.dumps(payload, ensure_ascii=False))
