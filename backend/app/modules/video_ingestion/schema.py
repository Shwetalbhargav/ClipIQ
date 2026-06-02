"""Pydantic schemas for the ClipIQ video ingestion module.

This module intentionally contains request/response contracts only. Keeping schema
objects separate from service code gives FastAPI clean OpenAPI generation, keeps
router handlers thin, and prevents transport-layer concerns from leaking into the
business logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, computed_field, field_validator


class SupportedPlatform(StrEnum):
    """Social platforms currently supported by ClipIQ ingestion."""

    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class TranscriptAvailability(StrEnum):
    """Represents whether transcript extraction is available for a video."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    NOT_REQUESTED = "not_requested"


class MetricAvailability(StrEnum):
    """Represents why a numeric metric may not be present in a response."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PRIVATE_OR_HIDDEN = "private_or_hidden"
    EXTRACTOR_UNSUPPORTED = "extractor_unsupported"


class VideoAnalyzeRequest(BaseModel):
    """Request body for POST /videos/analyze.

    The endpoint accepts a list to keep the API flexible while still enforcing
    the product rule that one YouTube URL and one Instagram Reel URL are needed
    for a comparison-oriented ClipIQ analysis.
    """

    model_config = ConfigDict(extra="forbid")

    urls: list[AnyHttpUrl] = Field(
        ...,
        min_length=2,
        max_length=2,
        description="Exactly two video URLs. ClipIQ supports one YouTube video and one Instagram Reel.",
        examples=[
            [
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.instagram.com/reel/CxYz123abcd/",
            ]
        ],
    )

    @field_validator("urls")
    @classmethod
    def validate_unique_urls(cls, urls: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        """Reject duplicate raw URLs and require one YouTube plus one Instagram URL."""

        normalized = {str(url).rstrip("/") for url in urls}
        if len(normalized) != len(urls):
            raise ValueError("Duplicate URLs are not allowed in a single analysis request.")
        from .utils import detect_platform

        platforms = [detect_platform(str(url)) for url in urls]
        if sorted(platform.value for platform in platforms) != ["instagram", "youtube"]:
            raise ValueError("Exactly one YouTube URL and one Instagram Reel URL are required.")
        return urls


class MetricValue(BaseModel):
    """Numeric metric wrapper that preserves unavailable-vs-zero semantics.

    Public social metrics are inconsistent. A missing value can mean the platform
    hid it, the extractor could not access it, or the metric does not exist for
    that platform. Returning a wrapper prevents downstream code from treating
    unavailable values as real zeroes.
    """

    model_config = ConfigDict(extra="forbid")

    value: int | None = Field(default=None, ge=0)
    availability: MetricAvailability = MetricAvailability.UNAVAILABLE
    reason: str | None = None

    @classmethod
    def available(cls, value: int | None) -> "MetricValue":
        """Create a metric wrapper from an extracted integer value."""

        if value is None:
            return cls(value=None, availability=MetricAvailability.UNAVAILABLE)
        return cls(value=value, availability=MetricAvailability.AVAILABLE)


class NormalizedVideoMetadata(BaseModel):
    """Canonical metadata shape returned by video ingestion.

    Every platform extractor maps into this schema so downstream systems do not
    need to know whether a value came from YouTube, Instagram, yt-dlp, or a future
    official API adapter.
    """

    model_config = ConfigDict(extra="forbid")

    video_id: str = Field(description="Stable platform video identifier or shortcode.")
    platform: SupportedPlatform
    source_url: AnyHttpUrl
    canonical_url: str
    creator: str | None = None
    creator_id: str | None = None
    follower_count: MetricValue = Field(default_factory=MetricValue)
    title: str | None = None
    caption: str | None = None
    description: str | None = None
    views: MetricValue = Field(default_factory=MetricValue)
    likes: MetricValue = Field(default_factory=MetricValue)
    comments: MetricValue = Field(default_factory=MetricValue)
    hashtags: list[str] = Field(default_factory=list)
    duration_seconds: float | None = Field(default=None, ge=0)
    upload_date: datetime | None = None
    thumbnail_url: str | None = None
    transcript_status: TranscriptAvailability = TranscriptAvailability.NOT_REQUESTED
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    @computed_field(return_type=float | None)
    @property
    def engagement_rate(self) -> float | None:
        """Calculate ((likes + comments) / views) * 100 when inputs are valid.

        The calculation returns ``None`` when views, likes, or comments are not
        available. That is deliberate because a hidden metric is not equivalent
        to zero and should not bias creator-facing analysis.
        """

        if self.views.value in (None, 0):
            return None
        if self.likes.value is None or self.comments.value is None:
            return None
        return round(((self.likes.value + self.comments.value) / self.views.value) * 100, 4)


class VideoAnalysisItem(BaseModel):
    """Single-video result object returned from the analysis endpoint."""

    model_config = ConfigDict(extra="forbid")

    label: Literal["A", "B"]
    metadata: NormalizedVideoMetadata


class VideoAnalyzeResponse(BaseModel):
    """Response body for POST /videos/analyze."""

    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID = Field(default_factory=uuid4)
    status: Literal["completed", "partial", "failed"]
    videos: list[VideoAnalysisItem]
    errors: list["VideoIngestionError"] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoIngestionError(BaseModel):
    """Structured error object safe to return to API clients."""

    model_config = ConfigDict(extra="forbid")

    url: str
    platform: SupportedPlatform | None = None
    code: str
    message: str
    retryable: bool = False


class ExtractedVideoPayload(BaseModel):
    """Internal normalized payload returned by platform extractor adapters."""

    model_config = ConfigDict(extra="allow")

    video_id: str
    platform: SupportedPlatform
    source_url: str
    canonical_url: str
    creator: str | None = None
    creator_id: str | None = None
    follower_count: int | None = None
    title: str | None = None
    caption: str | None = None
    description: str | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    hashtags: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None
    upload_date: datetime | None = None
    thumbnail_url: str | None = None
    transcript_status: TranscriptAvailability = TranscriptAvailability.NOT_REQUESTED
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


VideoAnalyzeResponse.model_rebuild()
