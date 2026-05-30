"""Pydantic schemas for ingestion endpoints."""

from pydantic import BaseModel, Field


class IngestionStartRequest(BaseModel):
    pdf_path: str = Field(..., min_length=1)
    chapter_id: int | None = None
    clear_existing: bool = False


class IngestionStartResponse(BaseModel):
    task_id: str
    status: str


class IngestionStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    chunks_created: int = 0
    pages_processed: int = 0
    errors: list[str] = []


class IngestionStatsResponse(BaseModel):
    total_chunks: int
    chunks_by_chapter: dict[str, int]
    avg_chunk_length: float
    pages_processed: int


class IngestionClearResponse(BaseModel):
    deleted_chunks: int


class TestChunkResponse(BaseModel):
    chunk: dict
    similar_chunks: list[dict]
