"""Schemas for ClipIQ retrieval.

The retrieval layer receives a user query, searches transcript chunk embeddings,
and returns ranked chunks plus citation metadata that the chat layer can pass to
LangGraph/LLM prompts and stream back to the frontend.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


VideoLabel = Literal["A", "B"]


class SourceKind(str, Enum):
    """Kinds of sources the assistant may cite."""

    TRANSCRIPT_CHUNK = "transcript_chunk"
    METADATA = "metadata"


class RetrievalFilter(BaseModel):
    """Metadata constraints used to keep retrieval scoped and safe.

    `comparison_id` is required because ClipIQ answers must only use the two
    videos in the active comparison session. Optional filters allow callers to
    narrow retrieval to one video/platform when the user asks a targeted question.
    """

    comparison_id: str = Field(..., min_length=1)
    video_id: str | None = Field(default=None, description="Internal video id.")
    video_label: VideoLabel | None = Field(default=None, description="Video A or B.")
    platform: str | None = Field(default=None, description="youtube or instagram")
    creator: str | None = None


class RetrievalRequest(BaseModel):
    """Input to the retrieval service."""

    query: str = Field(..., min_length=1)
    filters: RetrievalFilter
    top_k: int = Field(default=8, ge=1, le=20)
    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional minimum vector similarity score.",
    )

    @field_validator("query")
    @classmethod
    def clean_query(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValueError("query cannot be blank")
        return cleaned


class ChunkMetadata(BaseModel):
    """Payload metadata stored beside a vector point."""

    comparison_id: str
    video_id: str
    video_label: VideoLabel | None = None
    platform: str
    source_url: str | None = None
    creator: str | None = None
    chunk_id: str
    chunk_index: int = Field(..., ge=0)
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    title: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """A transcript chunk returned by similarity search."""

    id: str
    text: str
    score: float
    metadata: ChunkMetadata


class Citation(BaseModel):
    """Stable source label that can be attached to generated answers."""

    citation_id: str
    label: str
    source_kind: SourceKind = SourceKind.TRANSCRIPT_CHUNK
    video_id: str
    video_label: VideoLabel | None = None
    platform: str
    chunk_id: str
    chunk_index: int
    start_seconds: float | None = None
    end_seconds: float | None = None
    quoted_text: str
    score: float
    source_url: str | None = None


class RetrievalResult(BaseModel):
    """Output from retrieval: ranked chunks and generated citations."""

    query: str
    chunks: list[RetrievedChunk]
    citations: list[Citation]

    @property
    def has_sources(self) -> bool:
        return bool(self.chunks)
