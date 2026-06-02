"""Pydantic schemas for the ClipIQ chat module.

The chat module is intentionally small at the boundary: the router accepts a
session-scoped question and returns an answer plus citations. Internally the
service can stream through LangGraph or run a synchronous graph invocation, but
this response schema stays stable for the frontend and tests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRole(str, Enum):
    """Allowed chat message roles persisted in session memory."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CitationSourceType(str, Enum):
    """Types of evidence the assistant may cite.

    Transcript chunks are the primary citation source. Metadata citations are
    still first-class because engagement rate, creator, follower count, views,
    likes, comments, and upload date often come from structured extractor data
    rather than transcript text.
    """

    TRANSCRIPT_CHUNK = "transcript_chunk"
    VIDEO_METADATA = "video_metadata"


class ChatRequest(BaseModel):
    """Request body for POST /chat.

    `session_id` scopes memory and retrieval to the current video comparison.
    This is the critical guardrail that prevents sources from one creator's
    comparison from leaking into another creator's answer.
    """

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Comparison/session identifier returned by analysis flow.",
        examples=["8dc6cc4d-9fb8-4e6e-bb42-fc459f0f3a20"],
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=4_000,
        description="Creator's question about the current comparison.",
        examples=["Why did Video A get more engagement than Video B?"],
    )
    top_k: int = Field(
        default=8,
        ge=1,
        le=12,
        description="Maximum retrieved transcript chunks to pass into LangGraph.",
    )

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        """Trim whitespace and reject empty/whitespace-only messages."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("message cannot be blank")
        return normalized

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str) -> str:
        """Keep session ids URL/log friendly without forcing UUID-only sessions."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("session_id cannot be blank")
        return normalized


class ChatMessage(BaseModel):
    """A single chat memory item loaded into or persisted from the graph."""

    role: ChatRole
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceCitation(BaseModel):
    """Evidence surfaced with an answer.

    The label is intentionally human-readable (`Video A Chunk 3`) so the React
    UI can display it without needing to understand every backend id.
    """

    citation_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str = Field(..., examples=["Video A Chunk 3"])
    source_type: CitationSourceType = CitationSourceType.TRANSCRIPT_CHUNK
    video_id: Literal["A", "B"] | str = Field(..., examples=["A"])
    chunk_id: str | None = Field(default=None, examples=["chunk-A-003"])
    chunk_index: int | None = Field(default=None, ge=0, examples=[3])
    platform: str | None = Field(default=None, examples=["youtube"])
    start_seconds: float | None = Field(default=None, ge=0, examples=[0.0])
    end_seconds: float | None = Field(default=None, ge=0, examples=[5.0])
    text: str | None = Field(
        default=None,
        max_length=1_000,
        description="Short cited excerpt, not the full transcript chunk.",
    )
    score: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response body for POST /chat."""

    response_id: UUID = Field(default_factory=uuid4)
    session_id: str
    answer: str
    citations: list[SourceCitation] = Field(default_factory=list)
    model: str | None = Field(default=None, examples=["gpt-4o-mini"])
    usage: dict[str, Any] = Field(default_factory=dict)


class ChatErrorResponse(BaseModel):
    """Consistent error payload for client-friendly failures."""

    error: str
    detail: str | None = None


class RetrievedChunk(BaseModel):
    """Internal retrieval result normalized before entering LangGraph."""

    model_config = ConfigDict(extra="allow")

    chunk_id: str
    video_id: Literal["A", "B"] | str
    chunk_index: int
    text: str
    platform: str | None = None
    source_url: str | None = None
    creator: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_citation(self) -> SourceCitation:
        """Create a stable citation object from the retrieved chunk."""

        video_label = f"Video {self.video_id}"
        chunk_label = f"Chunk {self.chunk_index}"
        return SourceCitation(
            label=f"{video_label} {chunk_label}",
            video_id=self.video_id,
            chunk_id=self.chunk_id,
            chunk_index=self.chunk_index,
            platform=self.platform,
            start_seconds=self.start_seconds,
            end_seconds=self.end_seconds,
            text=self.text[:500],
            score=self.score,
            metadata=self.metadata,
        )
