"""Typed state objects for the ClipIQ LangGraph workflow.

The graph is intentionally state-first: every node receives a single state dict,
adds its own output, and returns only the changed fields. This makes each node
independently testable and keeps source grounding explicit across the workflow.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

VideoLabel = Literal["A", "B"]
MessageRole = Literal["system", "user", "assistant"]


class ChatMessage(TypedDict):
    """A compact chat message used for session-scoped memory."""

    role: MessageRole
    content: str


class Citation(TypedDict, total=False):
    """Citation emitted to the frontend and persisted with the assistant turn."""

    citation_id: str
    video_id: VideoLabel
    chunk_id: str
    chunk_index: int
    platform: str
    source_url: str
    start_seconds: float | None
    end_seconds: float | None
    text: str


class RetrievedChunk(TypedDict, total=False):
    """Transcript chunk returned by the retrieval layer.

    The retrieval adapter should already filter by comparison/session ID to avoid
    cross-session leakage. The graph still carries `comparison_id` and `video_id`
    so tests can verify source isolation.
    """

    chunk_id: str
    comparison_id: str
    video_id: VideoLabel
    platform: str
    source_url: str
    creator: str | None
    chunk_index: int
    start_seconds: float | None
    end_seconds: float | None
    text: str
    score: float | None


class VideoMetadata(TypedDict, total=False):
    """Normalized metadata used for factual, metadata-grounded answers."""

    video_id: VideoLabel
    platform: str
    source_url: str
    creator: str | None
    title: str | None
    published_at: str | None
    duration_seconds: int | None
    views: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    saves: int | None
    follower_count: int | None
    hashtags: list[str]
    engagement_rate: float | None
    engagement_formula: str | None
    transcript_status: str | None


class ComparisonSummary(TypedDict, total=False):
    """Computed comparison fields derived from metadata for answer generation."""

    winner_by_engagement_rate: VideoLabel | None
    engagement_rate_delta: float | None
    metadata_notes: list[str]


class GraphState(TypedDict):
    """State passed through the ClipIQ LangGraph flow.

    Required inputs:
    - comparison_id: session/comparison scope.
    - question: user question.

    Populated by nodes:
    - retrieved_a/retrieved_b: transcript evidence for each video.
    - metadata: normalized metadata for both videos.
    - comparison: deterministic metric comparison.
    - citations: source references used by the answer.
    - answer: final model response.
    """

    comparison_id: str
    question: str
    memory: NotRequired[list[ChatMessage]]
    metadata: NotRequired[dict[VideoLabel, VideoMetadata]]
    retrieved_a: NotRequired[list[RetrievedChunk]]
    retrieved_b: NotRequired[list[RetrievedChunk]]
    comparison: NotRequired[ComparisonSummary]
    citations: NotRequired[list[Citation]]
    context: NotRequired[str]
    answer: NotRequired[str]
    errors: NotRequired[list[str]]
    usage: NotRequired[dict[str, Any]]
