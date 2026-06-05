"""Schemas for the vector store module.

This module intentionally contains only lightweight Pydantic models and enums.
Keeping schemas separate from OpenAI/Qdrant clients makes the vector store easy to
unit test and keeps the service layer from depending on transport-specific types.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VideoLabel(str, Enum):
    """Human-friendly labels used throughout the comparison product."""

    VIDEO_A = "A"
    VIDEO_B = "B"


class VectorStoreSettings(BaseModel):
    """Runtime configuration for embeddings and Qdrant.

    Values should normally be loaded from environment variables by the app config
    layer and then passed into the vector store module. Keeping this as a plain
    Pydantic model avoids importing the global FastAPI settings object here.
    """

    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str | None = Field(default=None)
    qdrant_collection: str = Field(default="video_transcript_chunks")

    # text-embedding-3-small returns 1536 dimensions. Local models such as BGE/E5
    # are padded or truncated to qdrant_vector_size so existing collections work.
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    openai_api_key: str | None = Field(default=None)
    embedding_provider: Literal["openai", "sentence_transformers", "local_hash"] = Field(default="openai")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    qdrant_vector_size: int = Field(default=1536, gt=0)

    # Operational defaults: tuned for short-form transcript chunks, not giant docs.
    embedding_batch_size: int = Field(default=96, ge=1, le=2048)
    qdrant_write_batch_size: int = Field(default=128, ge=1, le=2048)
    qdrant_timeout_seconds: int = Field(default=30, ge=1, le=300)


class ChunkMetadata(BaseModel):
    """Metadata attached to every transcript chunk in Qdrant payload.

    Qdrant is not the system of record. The payload stays compact but contains
    enough information for retrieval filtering and source citation rendering.
    """

    model_config = ConfigDict(extra="allow")

    comparison_id: str = Field(..., min_length=1)
    video_id: str = Field(..., min_length=1, description="Video label, usually A or B")
    chunk_id: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)

    # Optional-but-useful citation/display fields.
    platform: Literal["youtube", "instagram", "unknown"] = "unknown"
    source_url: str | None = None
    creator: str | None = None
    title: str | None = None
    metadata_version: str = "v1"

    @field_validator("end_time")
    @classmethod
    def validate_time_range(cls, end_time: float | None, info: Any) -> float | None:
        """Reject inverted timestamps when both start and end are available."""

        start_time = info.data.get("start_time")
        if start_time is not None and end_time is not None and end_time < start_time:
            raise ValueError("end_time must be greater than or equal to start_time")
        return end_time

    def to_payload(self, text: str, embedding_model: str) -> dict[str, Any]:
        """Convert model data into a Qdrant-safe JSON payload."""

        payload = self.model_dump(mode="json", exclude_none=True)
        payload["text"] = text
        payload["embedding_model"] = embedding_model
        return payload


class TranscriptChunkInput(BaseModel):
    """Input accepted by the vector store when indexing transcript chunks."""

    text: str = Field(..., min_length=1)
    metadata: ChunkMetadata

    @field_validator("text")
    @classmethod
    def normalize_text(cls, text: str) -> str:
        """Collapse accidental whitespace before embedding.

        This avoids spending tokens on formatting noise and makes chunk hashes more
        stable across extractor variations.
        """

        cleaned = " ".join(text.split())
        if not cleaned:
            raise ValueError("text must contain non-whitespace content")
        return cleaned


class IndexedVector(BaseModel):
    """Result returned after a chunk has been written to Qdrant."""

    point_id: str
    comparison_id: str
    video_id: str
    chunk_id: str
    chunk_index: int


class VectorSearchRequest(BaseModel):
    """Search request used by RAG retrieval nodes."""

    query: str = Field(..., min_length=1)
    comparison_id: str = Field(..., min_length=1)
    video_id: str | None = Field(default=None, description="Optional filter for Video A or B")
    top_k: int = Field(default=8, ge=1, le=50)
    score_threshold: float | None = Field(default=None, ge=0, le=1)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, query: str) -> str:
        cleaned = " ".join(query.split())
        if not cleaned:
            raise ValueError("query must contain non-whitespace content")
        return cleaned


class VectorSearchResult(BaseModel):
    """Normalized result returned by Qdrant searches."""

    point_id: str
    score: float
    text: str
    metadata: ChunkMetadata

    @property
    def citation_label(self) -> str:
        """Stable citation label for downstream prompts and frontend display."""

        return f"Video {self.metadata.video_id} Chunk {self.metadata.chunk_index}"
