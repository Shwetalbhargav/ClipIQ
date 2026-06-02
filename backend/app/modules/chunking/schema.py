"""
Schema definitions for transcript chunking.

This module intentionally stays independent from any vector database or embedding
provider. Chunking should produce clean, validated data that later services can
embed and write to Qdrant/Chroma/Pinecone without knowing how the chunks were
created.

Chunking requirements:
- Default chunk size: 500 token-like words.
- Default overlap: 100 token-like words.
- Preserve timestamps.
- Generate chunk metadata suitable for citation and vector payload filtering.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from typing import Any, Literal


Platform = Literal["youtube", "instagram", "unknown"]


class TranscriptSegment(BaseModel):
    """
    Normalized transcript segment from an extractor.

    A segment usually maps to one caption line or one speech-to-text segment.
    Chunking should preserve these boundaries as much as possible, but it may
    split long segments when the text exceeds the configured chunk size.
    """

    segment_index: int = Field(..., ge=0)
    text: str = Field(..., min_length=1)
    start_seconds: float = Field(..., ge=0)
    end_seconds: float = Field(..., ge=0)
    source_type: str | None = Field(
        default=None,
        description="Example: manual_caption, auto_caption, whisper, unknown.",
    )

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Transcript segment text cannot be empty.")
        return cleaned

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "TranscriptSegment":
        if self.end_seconds < self.start_seconds:
            raise ValueError(
                "Transcript segment end_seconds cannot be earlier than start_seconds."
            )
        return self


class ChunkMetadata(BaseModel):
    """
    Metadata attached to every transcript chunk.

    This object is intentionally shaped so it can be stored directly as vector DB
    payload metadata. It also contains enough information to render citations like:

        Video A · Chunk 3 · 00:12-00:24

    Keep metadata compact. Large raw extraction payloads belong in MongoDB or the
    primary app database, not inside the vector store.
    """

    comparison_id: str | None = Field(
        default=None,
        description="Session/comparison scope. Required for production retrieval filtering.",
    )
    video_id: str = Field(
        ...,
        min_length=1,
        description="Internal video label or ID, such as A, B, or a database UUID.",
    )
    platform: Platform = "unknown"
    source_url: str | None = None
    creator: str | None = None

    chunk_index: int = Field(..., ge=0)
    chunk_id: str = Field(
        ...,
        description="Stable deterministic chunk identifier.",
    )

    start_seconds: float = Field(..., ge=0)
    end_seconds: float = Field(..., ge=0)

    token_count: int = Field(..., ge=1)
    char_count: int = Field(..., ge=1)

    segment_start_index: int = Field(..., ge=0)
    segment_end_index: int = Field(..., ge=0)
    source_segment_indices: list[int] = Field(default_factory=list)

    chunk_size: int = Field(..., ge=1)
    overlap: int = Field(..., ge=0)

    metadata_version: str = "chunking.v1"
    chunk_strategy: str = "segment_preserving_sliding_window"

    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Small optional fields needed by downstream systems.",
    )

    @model_validator(mode="after")
    def validate_timestamp_order(self) -> "ChunkMetadata":
        if self.end_seconds < self.start_seconds:
            raise ValueError("Chunk end_seconds cannot be earlier than start_seconds.")
        if self.segment_end_index < self.segment_start_index:
            raise ValueError(
                "segment_end_index cannot be earlier than segment_start_index."
            )
        return self
    
    def to_payload(self) -> dict[str, Any]:
        """
        Convert chunk metadata into a vector-database-friendly payload.

        Qdrant/Chroma payloads should be flat and JSON-serializable. We keep the
        core citation/filtering fields at the top level, then merge in small
        optional metadata from `extra`.

        The `extra` dictionary is merged last on purpose so downstream callers
        can add fields like `platform_video_id` without changing the schema.
        """

        payload = self.model_dump(exclude={"extra"})

        if self.extra:
            payload.update(self.extra)

        return payload


class TranscriptChunk(BaseModel):
    """
    Final chunk object produced by the chunking service.

    The embedding pipeline should embed `text` and store `metadata` as vector DB
    payload. The database layer may additionally persist this object as a durable
    transcript_chunks record.
    """

    text: str = Field(..., min_length=1)
    metadata: ChunkMetadata

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Chunk text cannot be empty.")
        return cleaned


class ChunkingRequest(BaseModel):
    """
    Input contract for chunking a single video's transcript.
    """

    segments: list[TranscriptSegment] = Field(..., min_length=1)

    video_id: str = Field(..., min_length=1)
    comparison_id: str | None = None
    platform: Platform = "unknown"
    source_url: str | None = None
    creator: str | None = None

    chunk_size: int = Field(
        default=500,
        ge=1,
        description="Maximum token-like words per chunk.",
    )
    overlap: int = Field(
        default=100,
        ge=0,
        description="Token-like words repeated between adjacent chunks.",
    )

    metadata_extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_chunk_window(self) -> "ChunkingRequest":
        if self.overlap >= self.chunk_size:
            raise ValueError("overlap must be smaller than chunk_size.")
        return self


class ChunkingResult(BaseModel):
    """
    Output contract for chunking.

    `chunks` can be passed directly to the embedding/indexing module.
    """

    video_id: str
    comparison_id: str | None = None
    total_segments: int
    total_chunks: int
    chunk_size: int
    overlap: int
    chunks: list[TranscriptChunk]

    