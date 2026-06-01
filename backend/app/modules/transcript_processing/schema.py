"""Schemas for ClipIQ transcript processing.

This module intentionally keeps schema objects independent from FastAPI, MongoDB,
Qdrant, or any specific extractor implementation. The transcript processing layer
can therefore be used by API handlers, background workers, tests, and future
platform-specific extractors without pulling in web-framework dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TranscriptSource(str, Enum):
    """Where transcript text came from.

    Caption-first extraction is cheaper and faster than speech-to-text. Whisper is
    modeled as a fallback source so downstream code can explain transcript quality,
    latency, and cost tradeoffs to users/operators.
    """

    MANUAL_CAPTIONS = "manual_captions"
    AUTO_CAPTIONS = "auto_captions"
    YT_DLP_CAPTIONS = "yt_dlp_captions"
    WHISPER = "whisper"
    UNKNOWN = "unknown"


class TranscriptStatus(str, Enum):
    """Processing status for a transcript request."""

    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(slots=True)
class TranscriptProcessingConfig:
    """Runtime configuration for transcript extraction and chunking.

    Attributes:
        enable_whisper_fallback: Whether the service may download audio and run
            Whisper when captions/transcripts are unavailable.
        whisper_model: Local Whisper model name, or provider model name if using
            a managed transcription client in the future.
        language: Optional language hint such as ``"en"``. ``None`` lets the
            extractor/provider auto-detect.
        max_video_duration_seconds: Safety guardrail to avoid downloading or
            transcribing long videos in an MVP/demo environment.
        target_chunk_seconds: Preferred chunk duration. The chunker tries to
            preserve transcript segment boundaries while approaching this size.
        max_chunk_chars: Hard text-size limit for one chunk. This keeps embedding
            requests bounded and prevents oversized retrieval payloads.
        chunk_overlap_seconds: Timestamp overlap between neighboring chunks.
            Useful when a hook/thought spans a boundary.
        temp_dir: Directory for temporary media downloads used by Whisper.
    """

    enable_whisper_fallback: bool = True
    whisper_model: str = "base"
    language: Optional[str] = None
    max_video_duration_seconds: int = 10 * 60
    target_chunk_seconds: float = 30.0
    max_chunk_chars: int = 1_500
    chunk_overlap_seconds: float = 2.0
    temp_dir: str = "/tmp/clipiq_transcripts"


@dataclass(slots=True)
class TranscriptSegment:
    """A timestamped transcript segment normalized across providers."""

    segment_index: int
    text: str
    start_seconds: float
    end_seconds: float
    source_type: TranscriptSource
    confidence: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Normalize text and validate timestamp ordering."""
        self.text = " ".join((self.text or "").split())
        self.start_seconds = max(0.0, float(self.start_seconds or 0.0))
        self.end_seconds = max(self.start_seconds, float(self.end_seconds or self.start_seconds))


@dataclass(slots=True)
class TranscriptChunk:
    """Embedding-ready transcript chunk with source metadata."""

    chunk_index: int
    text: str
    start_seconds: float
    end_seconds: float
    segment_indices: List[int]
    source_type: TranscriptSource
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TranscriptExtractionRequest:
    """Input contract for transcript extraction.

    ``video_id`` is the application's stable Video A/B or DB identifier, while
    ``platform_video_id`` is the native platform identifier/shortcode when known.
    """

    video_id: str
    source_url: str
    platform: str
    platform_video_id: Optional[str] = None
    preferred_languages: List[str] = field(default_factory=lambda: ["en"])
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TranscriptExtractionResult:
    """Complete transcript processing output.

    The service returns this object even when extraction fails or is unavailable,
    allowing API/workers to persist partial results instead of crashing the whole
    comparison session.
    """

    video_id: str
    status: TranscriptStatus
    source_type: TranscriptSource
    segments: List[TranscriptSegment] = field(default_factory=list)
    chunks: List[TranscriptChunk] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def transcript_text(self) -> str:
        """Return the full transcript as one normalized string."""
        return " ".join(segment.text for segment in self.segments if segment.text).strip()


class TranscriptProcessingError(RuntimeError):
    """Base exception for expected transcript-processing failures."""


class TranscriptUnavailableError(TranscriptProcessingError):
    """Raised when no captions/transcript can be found and fallback is disabled."""


class WhisperTranscriptionError(TranscriptProcessingError):
    """Raised when Whisper fallback is enabled but transcription fails."""
