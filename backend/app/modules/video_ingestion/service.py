"""Business logic for ClipIQ video metadata ingestion.

The service exposes a small orchestration API that validates URLs, delegates
platform-specific extraction to adapters, maps raw extractor payloads into the
canonical ClipIQ metadata schema, and returns Pydantic response models only.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

try:  # yt-dlp is optional at import time so tests can run without network tooling.
    import yt_dlp  # type: ignore
except Exception:  # pragma: no cover - dependency availability differs by env.
    yt_dlp = None  # type: ignore

from .schema import (
    ExtractedVideoPayload,
    MetricValue,
    NormalizedVideoMetadata,
    SupportedPlatform,
    TranscriptAvailability,
    VideoAnalysisItem,
    VideoAnalyzeResponse,
    VideoIngestionError,
)
from .utils import (
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

logger = logging.getLogger(__name__)


class VideoIngestionException(Exception):
    """Base exception for expected ingestion failures."""

    code = "VIDEO_INGESTION_FAILED"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        platform: SupportedPlatform | None = None,
        code: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.platform = platform
        self.code = code or self.code
        self.retryable = self.retryable if retryable is None else retryable


class VideoExtractionException(VideoIngestionException):
    """Raised when a platform extractor fails to fetch or parse metadata."""

    code = "VIDEO_EXTRACTION_FAILED"
    retryable = True


class PlatformAuthenticationRequiredException(VideoExtractionException):
    """Raised when a provider blocks public extraction and needs cookies/login."""

    code = "PLATFORM_AUTHENTICATION_REQUIRED"
    retryable = False


class VideoValidationException(VideoIngestionException):
    """Raised when URL validation fails before extraction."""

    code = "VIDEO_URL_INVALID"
    retryable = False


class BaseVideoExtractor(ABC):
    """Abstract interface implemented by all platform extractors.

    The adapter boundary is the main business-logic decision in this module:
    YouTube and Instagram extraction methods are brittle and provider-dependent,
    but the rest of ClipIQ should consume one stable schema. New official API,
    browser-based, or cached extractors can replace these implementations without
    changing routers or downstream RAG code.
    """

    platform: SupportedPlatform

    @abstractmethod
    async def extract(self, url: str) -> ExtractedVideoPayload:
        """Extract and normalize platform metadata for a single video URL."""


@dataclass(frozen=True)
class YtDlpOptions:
    """Runtime options for the yt-dlp-backed extractor adapters."""

    timeout_seconds: int = 45
    cookies_file: str | None = None
    youtube_cookies_file: str | None = None
    instagram_cookies_file: str | None = None


class YtDlpVideoExtractor(BaseVideoExtractor):
    """yt-dlp-backed extractor used for YouTube and Instagram public metadata.

    ``yt-dlp`` is intentionally treated as an implementation detail. It is useful
    for demos and public metadata, while production can swap this class for an
    official API or user-authorized data provider when platform constraints call
    for it.
    """

    def __init__(self, platform: SupportedPlatform, options: YtDlpOptions | None = None) -> None:
        self.platform = platform
        self.options = options or YtDlpOptions()

    async def extract(self, url: str) -> ExtractedVideoPayload:
        """Fetch metadata through yt-dlp and map it into ClipIQ's internal payload."""

        if yt_dlp is None:
            raise VideoExtractionException(
                "yt-dlp is not installed. Install yt-dlp or configure another extractor.",
                platform=self.platform,
            )

        logger.info("Starting %s metadata extraction", self.platform.value, extra={"url": url})
        raw = await asyncio.to_thread(self._extract_blocking, url)
        payload = self._map_yt_dlp_payload(url, raw)
        logger.info(
            "Completed %s metadata extraction",
            self.platform.value,
            extra={"url": url, "video_id": payload.video_id},
        )
        return payload

    def _extract_blocking(self, url: str) -> dict[str, Any]:
        """Run yt-dlp synchronously inside a thread to avoid blocking the event loop."""

        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "socket_timeout": self.options.timeout_seconds,
            # Keeping playlists disabled prevents accidental multi-video work and
            # reduces surprise cost/latency from malformed user URLs.
            "noplaylist": True,
        }
        cookies_file = self._cookies_file()
        if cookies_file:
            ydl_opts["cookiefile"] = cookies_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[attr-defined]
                result = ydl.extract_info(url, download=False)
        except Exception as exc:  # pragma: no cover - network/provider behavior.
            raise self._to_extraction_exception(exc) from exc

        if not isinstance(result, dict):
            raise VideoExtractionException(
                f"Extractor returned an unexpected payload for {self.platform.value}.",
                platform=self.platform,
            )
        return result

    def _cookies_file(self) -> str | None:
        """Return platform-specific cookies first, then a shared fallback."""

        if self.platform == SupportedPlatform.YOUTUBE and self.options.youtube_cookies_file:
            return self.options.youtube_cookies_file
        if self.platform == SupportedPlatform.INSTAGRAM and self.options.instagram_cookies_file:
            return self.options.instagram_cookies_file
        return self.options.cookies_file

    def _to_extraction_exception(self, exc: Exception) -> VideoExtractionException:
        message = str(exc)
        lowered = message.lower()
        auth_markers = (
            "sign in to confirm",
            "not a bot",
            "login required",
            "rate-limit reached",
            "requested content is not available",
            "use --cookies",
            "use --cookies-from-browser",
        )
        if any(marker in lowered for marker in auth_markers):
            return PlatformAuthenticationRequiredException(
                (
                    f"{self.platform.value.title()} blocked public metadata extraction. "
                    "Configure a yt-dlp cookies file on the backend and retry."
                ),
                platform=self.platform,
            )
        return VideoExtractionException(
            f"Could not extract metadata from {self.platform.value}.",
            platform=self.platform,
        )

    def _map_yt_dlp_payload(self, url: str, raw: dict[str, Any]) -> ExtractedVideoPayload:
        """Map heterogeneous yt-dlp keys into the internal extraction payload."""

        title = raw.get("title")
        description = raw.get("description")
        caption = raw.get("description") if self.platform == SupportedPlatform.INSTAGRAM else None
        tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
        hashtags = sorted({*extract_hashtags(title, description, caption), *[str(tag).lower().lstrip("#") for tag in tags]})

        views = coerce_int(raw.get("view_count") or raw.get("play_count"))
        likes = coerce_int(raw.get("like_count"))
        comments = coerce_int(raw.get("comment_count"))
        follower_count = coerce_int(
            raw.get("channel_follower_count")
            or raw.get("uploader_follower_count")
            or raw.get("creator_follower_count")
            or raw.get("followers")
        )

        return ExtractedVideoPayload(
            video_id=str(raw.get("id") or extract_platform_video_id(url)),
            platform=self.platform,
            source_url=url,
            canonical_url=canonicalize_url(url),
            creator=raw.get("uploader") or raw.get("channel") or raw.get("creator"),
            creator_id=raw.get("uploader_id") or raw.get("channel_id"),
            follower_count=follower_count,
            title=title,
            caption=caption,
            description=description,
            views=views,
            likes=likes,
            comments=comments,
            hashtags=hashtags,
            duration_seconds=coerce_float(raw.get("duration")),
            upload_date=parse_upload_date(raw.get("upload_date") or raw.get("timestamp")),
            thumbnail_url=raw.get("thumbnail"),
            transcript_status=TranscriptAvailability.NOT_REQUESTED,
            raw_metadata=raw,
        )


class VideoIngestionService:
    """Application service that orchestrates video metadata extraction."""

    def __init__(self, extractors: dict[SupportedPlatform, BaseVideoExtractor] | None = None) -> None:
        self.extractors = extractors or self._default_extractors()

    @staticmethod
    def _default_extractors() -> dict[SupportedPlatform, BaseVideoExtractor]:
        from app.core.config import get_settings

        settings = get_settings()
        options = YtDlpOptions(
            timeout_seconds=settings.ytdlp_timeout_seconds,
            cookies_file=settings.ytdlp_cookies_file,
            youtube_cookies_file=settings.youtube_cookies_file,
            instagram_cookies_file=settings.instagram_cookies_file,
        )
        return {
            SupportedPlatform.YOUTUBE: YtDlpVideoExtractor(SupportedPlatform.YOUTUBE, options),
            SupportedPlatform.INSTAGRAM: YtDlpVideoExtractor(SupportedPlatform.INSTAGRAM, options),
        }

    async def analyze_videos(self, urls: Sequence[str]) -> VideoAnalyzeResponse:
        """Analyze one or more supported video URLs and return normalized metadata.

        Args:
            urls: User-submitted YouTube or Instagram Reel URLs.

        Returns:
            A Pydantic response model containing successfully extracted videos and
            structured per-video errors for partial failures.
        """

        logger.info("Received video analysis request", extra={"url_count": len(urls)})
        prepared_urls, validation_errors = self._validate_and_prepare_urls(urls)

        extraction_tasks = [self._safe_extract(url, label) for label, url in prepared_urls]
        extracted_results = await asyncio.gather(*extraction_tasks) if extraction_tasks else []

        videos: list[VideoAnalysisItem] = []
        errors: list[VideoIngestionError] = [*validation_errors]

        for item, error in extracted_results:
            if item is not None:
                videos.append(item)
            if error is not None:
                errors.append(error)

        status = "completed" if videos and not errors else "partial" if videos else "failed"
        logger.info(
            "Video analysis finished",
            extra={"status": status, "video_count": len(videos), "error_count": len(errors)},
        )
        return VideoAnalyzeResponse(status=status, videos=videos, errors=errors)

    def _validate_and_prepare_urls(self, urls: Sequence[str]) -> tuple[list[tuple[str, str]], list[VideoIngestionError]]:
        """Validate URLs, canonicalize them, and assign stable Video A/B labels."""

        prepared: list[tuple[str, str]] = []
        errors: list[VideoIngestionError] = []
        seen_canonical_urls: set[str] = set()

        for index, raw_url in enumerate(urls):
            url = str(raw_url)
            try:
                platform = detect_platform(url)
                canonical_url = canonicalize_url(url)
                if canonical_url in seen_canonical_urls:
                    raise VideoValidationException("Duplicate canonical video URLs are not allowed.", platform=platform)
                seen_canonical_urls.add(canonical_url)
                prepared.append(("A" if index == 0 else "B", canonical_url))
            except (UnsupportedVideoUrlError, InvalidVideoUrlError, VideoValidationException) as exc:
                errors.append(
                    VideoIngestionError(
                        url=url,
                        platform=getattr(exc, "platform", None),
                        code=getattr(exc, "code", "VIDEO_URL_INVALID"),
                        message=str(exc),
                        retryable=getattr(exc, "retryable", False),
                    )
                )

        return prepared, errors

    async def _safe_extract(self, url: str, label: str) -> tuple[VideoAnalysisItem | None, VideoIngestionError | None]:
        """Extract one video while converting expected failures into response errors."""

        try:
            platform = detect_platform(url)
            extractor = self.extractors.get(platform)
            if extractor is None:
                raise VideoValidationException(f"No extractor configured for {platform.value}.", platform=platform)
            payload = await extractor.extract(url)
            metadata = self._to_public_metadata(payload)
            return VideoAnalysisItem(label=label, metadata=metadata), None
        except VideoIngestionException as exc:
            logger.warning(
                "Video ingestion failed",
                exc_info=True,
                extra={"url": url, "platform": getattr(exc.platform, "value", None), "code": exc.code},
            )
            return None, VideoIngestionError(
                url=url,
                platform=exc.platform,
                code=exc.code,
                message=str(exc),
                retryable=exc.retryable,
            )
        except Exception as exc:  # pragma: no cover - final safety net.
            logger.exception("Unexpected video ingestion error", extra={"url": url})
            return None, VideoIngestionError(
                url=url,
                platform=None,
                code="UNEXPECTED_VIDEO_INGESTION_ERROR",
                message="Unexpected error while analyzing the video.",
                retryable=True,
            )

    def _to_public_metadata(self, payload: ExtractedVideoPayload) -> NormalizedVideoMetadata:
        """Convert internal extractor payload into the API response schema."""

        return NormalizedVideoMetadata(
            video_id=payload.video_id,
            platform=payload.platform,
            source_url=payload.source_url,
            canonical_url=payload.canonical_url,
            creator=payload.creator,
            creator_id=payload.creator_id,
            follower_count=MetricValue.available(payload.follower_count),
            title=payload.title,
            caption=payload.caption,
            description=payload.description,
            views=MetricValue.available(payload.views),
            likes=MetricValue.available(payload.likes),
            comments=MetricValue.available(payload.comments),
            hashtags=payload.hashtags,
            duration_seconds=payload.duration_seconds,
            upload_date=payload.upload_date,
            thumbnail_url=payload.thumbnail_url,
            transcript_status=payload.transcript_status,
            raw_metadata=payload.raw_metadata,
        )


def get_video_ingestion_service() -> VideoIngestionService:
    """FastAPI dependency factory for the video ingestion service."""

    return VideoIngestionService()
