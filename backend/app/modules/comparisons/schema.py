"""Schemas for end-to-end ClipIQ video comparisons."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.modules.video_ingestion.schema import SupportedPlatform
from app.modules.video_ingestion.utils import InvalidVideoUrlError, UnsupportedVideoUrlError, detect_platform


ComparisonStatus = Literal["ready", "partial", "failed"]


class ComparisonAnalyzeRequest(BaseModel):
    """Strict request model for the screening-required comparison flow."""

    model_config = ConfigDict(extra="forbid")

    youtube_url: HttpUrl
    instagram_url: HttpUrl

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, value: HttpUrl) -> HttpUrl:
        try:
            if detect_platform(str(value)) != SupportedPlatform.YOUTUBE:
                raise ValueError("youtube_url must be a YouTube video URL")
        except (UnsupportedVideoUrlError, InvalidVideoUrlError) as exc:
            raise ValueError("youtube_url must be a supported YouTube video URL") from exc
        return value

    @field_validator("instagram_url")
    @classmethod
    def validate_instagram_url(cls, value: HttpUrl) -> HttpUrl:
        try:
            if detect_platform(str(value)) != SupportedPlatform.INSTAGRAM:
                raise ValueError("instagram_url must be an Instagram Reel URL")
        except (UnsupportedVideoUrlError, InvalidVideoUrlError) as exc:
            raise ValueError("instagram_url must be a supported Instagram Reel URL") from exc
        return value


class VideoSummary(BaseModel):
    """Public summary returned for each side of a comparison."""

    label: Literal["A", "B"]
    video_id: str
    platform: Literal["youtube", "instagram"]
    source_url: str
    canonical_url: str | None = None
    creator: str | None = None
    follower_count: int | None = None
    title: str | None = None
    caption: str | None = None
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    engagement_rate: float | None = None
    hashtags: list[str] = Field(default_factory=list)
    upload_date: datetime | None = None
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    transcript_status: str = "unavailable"
    chunk_count: int = 0
    indexed_chunk_count: int = 0


class ComparisonAnalyzeResponse(BaseModel):
    """Response from POST /api/comparisons."""

    comparison_id: str
    status: ComparisonStatus
    video_a: VideoSummary | None = None
    video_b: VideoSummary | None = None
    transcript_status: dict[str, str] = Field(default_factory=dict)
    indexing_status: dict[str, str] = Field(default_factory=dict)
    engagement: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ComparisonGetResponse(ComparisonAnalyzeResponse):
    """Response from GET /api/comparisons/{comparison_id}."""

