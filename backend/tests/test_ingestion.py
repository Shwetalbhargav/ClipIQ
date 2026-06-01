"""Tests for ClipIQ's video ingestion module.

These tests intentionally avoid live calls to YouTube, Instagram, or yt-dlp.
The ingestion service is tested through fake extractor adapters so CI remains
fast, deterministic, and safe to run without platform credentials.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Sequence

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.video_ingestion.router import router, get_video_ingestion_service
from app.modules.video_ingestion.schema import (
    ExtractedVideoPayload,
    MetricAvailability,
    MetricValue,
    NormalizedVideoMetadata,
    SupportedPlatform,
    TranscriptAvailability,
    VideoAnalyzeResponse,
)
from app.modules.video_ingestion.service import BaseVideoExtractor, VideoIngestionService
from app.modules.video_ingestion.utils import (
    InvalidVideoUrlError,
    UnsupportedVideoUrlError,
    canonicalize_url,
    coerce_float,
    coerce_int,
    detect_platform,
    extract_hashtags,
    extract_platform_video_id,
    parse_upload_date,
)


class FakeExtractor(BaseVideoExtractor):
    """Deterministic test extractor that returns supplied payloads by platform."""

    def __init__(self, platform: SupportedPlatform, payload: ExtractedVideoPayload) -> None:
        self.platform = platform
        self._payload = payload
        self.seen_urls: list[str] = []

    async def extract(self, url: str) -> ExtractedVideoPayload:
        """Capture the canonical URL passed by the service and return fake metadata."""

        self.seen_urls.append(url)
        return self._payload.model_copy(update={"source_url": url, "canonical_url": canonicalize_url(url)})


class FailingExtractor(BaseVideoExtractor):
    """Extractor double that simulates a platform-side failure."""

    platform = SupportedPlatform.INSTAGRAM

    async def extract(self, url: str) -> ExtractedVideoPayload:
        """Raise a generic exception to exercise the service safety net."""

        raise RuntimeError("provider blocked request")


def _youtube_payload() -> ExtractedVideoPayload:
    """Return representative normalized YouTube extractor output."""

    return ExtractedVideoPayload(
        video_id="dQw4w9WgXcQ",
        platform=SupportedPlatform.YOUTUBE,
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        canonical_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        creator="Example Channel",
        creator_id="UC-example",
        follower_count=250_000,
        title="Great hook in 5 seconds #Marketing",
        description="A test description #Growth",
        views=10_000,
        likes=800,
        comments=200,
        hashtags=["marketing", "growth"],
        duration_seconds=42.5,
        upload_date=datetime(2024, 5, 1, tzinfo=timezone.utc),
        thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        transcript_status=TranscriptAvailability.NOT_REQUESTED,
        raw_metadata={"extractor": "fake-youtube"},
    )


def _instagram_payload() -> ExtractedVideoPayload:
    """Return representative normalized Instagram Reel extractor output."""

    return ExtractedVideoPayload(
        video_id="CxYz123abcd",
        platform=SupportedPlatform.INSTAGRAM,
        source_url="https://www.instagram.com/reel/CxYz123abcd/",
        canonical_url="https://www.instagram.com/reel/CxYz123abcd/",
        creator="example_creator",
        creator_id="ig-example",
        follower_count=50_000,
        caption="Testing a creator Reel #CreatorTips",
        views=5_000,
        likes=250,
        comments=50,
        hashtags=["creatortips"],
        duration_seconds=18.0,
        upload_date=datetime(2024, 5, 2, tzinfo=timezone.utc),
        thumbnail_url="https://example.com/reel.jpg",
        transcript_status=TranscriptAvailability.NOT_REQUESTED,
        raw_metadata={"extractor": "fake-instagram"},
    )


def _service_with_fakes() -> VideoIngestionService:
    """Build the ingestion service with deterministic platform adapters."""

    return VideoIngestionService(
        extractors={
            SupportedPlatform.YOUTUBE: FakeExtractor(SupportedPlatform.YOUTUBE, _youtube_payload()),
            SupportedPlatform.INSTAGRAM: FakeExtractor(SupportedPlatform.INSTAGRAM, _instagram_payload()),
        }
    )


def test_url_platform_detection_and_canonicalization() -> None:
    """Supported URLs should be detected and normalized into stable cache keys."""

    assert detect_platform("https://youtu.be/dQw4w9WgXcQ?t=1") == SupportedPlatform.YOUTUBE
    assert detect_platform("https://www.instagram.com/reel/CxYz123abcd/?igsh=test") == SupportedPlatform.INSTAGRAM
    assert canonicalize_url("https://youtu.be/dQw4w9WgXcQ?t=1") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert canonicalize_url("https://www.youtube.com/shorts/dQw4w9WgXcQ?feature=share") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert canonicalize_url("https://www.instagram.com/reel/CxYz123abcd/?utm_source=x") == "https://www.instagram.com/reel/CxYz123abcd/"
    assert extract_platform_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_platform_video_id("https://www.instagram.com/reel/CxYz123abcd/") == "CxYz123abcd"


def test_url_validation_rejects_unsupported_and_malformed_urls() -> None:
    """Unsupported domains and malformed platform URLs should fail before extraction."""

    with pytest.raises(UnsupportedVideoUrlError):
        detect_platform("https://www.tiktok.com/@creator/video/123")

    with pytest.raises(InvalidVideoUrlError):
        canonicalize_url("https://www.youtube.com/watch?v=")

    with pytest.raises(InvalidVideoUrlError):
        canonicalize_url("https://www.instagram.com/explore/tags/creator/")


def test_metadata_helpers_are_deterministic_and_safe() -> None:
    """Utility coercion should avoid fabricating metrics from bad extractor values."""

    assert extract_hashtags("Try this #AI", "Another #ai and #Growth") == ["ai", "growth"]
    assert parse_upload_date("20240501") == datetime(2024, 5, 1, tzinfo=timezone.utc)
    assert parse_upload_date("2024-05-01T10:15:00Z") == datetime(2024, 5, 1, 10, 15, tzinfo=timezone.utc)
    assert coerce_int("1,234") == 1234
    assert coerce_int(-1) is None
    assert coerce_int(True) is None
    assert coerce_float("42.5") == 42.5
    assert coerce_float("not-a-number") is None


def test_metric_value_and_engagement_rate_preserve_unavailable_semantics() -> None:
    """Missing metrics should stay unavailable and engagement rate should become null."""

    assert MetricValue.available(0).availability == MetricAvailability.AVAILABLE
    assert MetricValue.available(None).availability == MetricAvailability.UNAVAILABLE

    metadata = NormalizedVideoMetadata(
        video_id="abc123",
        platform=SupportedPlatform.YOUTUBE,
        source_url="https://www.youtube.com/watch?v=abc1234",
        canonical_url="https://www.youtube.com/watch?v=abc1234",
        views=MetricValue.available(10_000),
        likes=MetricValue.available(800),
        comments=MetricValue.available(200),
    )
    assert metadata.engagement_rate == 10.0

    missing_comments = metadata.model_copy(update={"comments": MetricValue.available(None)})
    assert missing_comments.engagement_rate is None

    zero_views = metadata.model_copy(update={"views": MetricValue.available(0)})
    assert zero_views.engagement_rate is None


def test_service_returns_completed_response_with_normalized_video_metadata() -> None:
    """The service should map fake extractor payloads into public Pydantic schemas."""

    response = asyncio.run(
        _service_with_fakes().analyze_videos(
            [
                "https://youtu.be/dQw4w9WgXcQ?t=99",
                "https://www.instagram.com/reel/CxYz123abcd/?utm_source=copy_link",
            ]
        )
    )

    assert isinstance(response, VideoAnalyzeResponse)
    assert response.status == "completed"
    assert response.errors == []
    assert [video.label for video in response.videos] == ["A", "B"]

    youtube = response.videos[0].metadata
    instagram = response.videos[1].metadata

    assert youtube.platform == SupportedPlatform.YOUTUBE
    assert youtube.canonical_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert youtube.creator == "Example Channel"
    assert youtube.views.value == 10_000
    assert youtube.engagement_rate == 10.0

    assert instagram.platform == SupportedPlatform.INSTAGRAM
    assert instagram.canonical_url == "https://www.instagram.com/reel/CxYz123abcd/"
    assert instagram.creator == "example_creator"
    assert instagram.engagement_rate == 6.0


def test_service_returns_partial_response_when_one_extractor_fails() -> None:
    """One platform failure should not discard successful metadata from the other URL."""

    service = VideoIngestionService(
        extractors={
            SupportedPlatform.YOUTUBE: FakeExtractor(SupportedPlatform.YOUTUBE, _youtube_payload()),
            SupportedPlatform.INSTAGRAM: FailingExtractor(),
        }
    )

    response = asyncio.run(
        service.analyze_videos(
            [
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.instagram.com/reel/CxYz123abcd/",
            ]
        )
    )

    assert response.status == "partial"
    assert len(response.videos) == 1
    assert response.videos[0].metadata.platform == SupportedPlatform.YOUTUBE
    assert len(response.errors) == 1
    assert response.errors[0].code == "UNEXPECTED_VIDEO_INGESTION_ERROR"
    assert response.errors[0].retryable is True


def test_service_returns_failed_response_for_invalid_only_request() -> None:
    """Requests with no extractable supported URLs should produce a failed response."""

    response = asyncio.run(_service_with_fakes().analyze_videos(["https://example.com/video/123"]))

    assert response.status == "failed"
    assert response.videos == []
    assert response.errors[0].code == "VIDEO_URL_INVALID"


def test_fastapi_route_uses_service_dependency_and_returns_schema_json() -> None:
    """The router should stay thin and delegate all business logic to the service."""

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_video_ingestion_service] = _service_with_fakes

    client = TestClient(app)
    response = client.post(
        "/videos/analyze",
        json={
            "urls": [
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.instagram.com/reel/CxYz123abcd/",
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["videos"][0]["label"] == "A"
    assert body["videos"][0]["metadata"]["engagement_rate"] == 10.0
    assert body["videos"][1]["label"] == "B"
    assert body["videos"][1]["metadata"]["platform"] == "instagram"
    assert body["errors"] == []


def test_fastapi_route_returns_422_when_service_status_failed() -> None:
    """A fully failed analysis should become a client-visible 422 error."""

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_video_ingestion_service] = _service_with_fakes

    client = TestClient(app)
    response = client.post("/videos/analyze", json={"urls": ["https://example.com/video/123"]})

    assert response.status_code == 422
    assert response.json()["detail"][0]["code"] == "VIDEO_URL_INVALID"
