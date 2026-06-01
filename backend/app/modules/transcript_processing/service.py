"""Transcript extraction and chunking service for ClipIQ.

The implementation follows a caption-first strategy: try cheap platform captions
first, then optionally fall back to Whisper speech-to-text. The service always
returns structured results with status/warnings/errors so one failed transcript
never crashes the entire video-comparison workflow.
"""

from __future__ import annotations

import json
import logging
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .schema import (
    TranscriptChunk,
    TranscriptExtractionRequest,
    TranscriptExtractionResult,
    TranscriptProcessingConfig,
    TranscriptProcessingError,
    TranscriptSegment,
    TranscriptSource,
    TranscriptStatus,
    TranscriptUnavailableError,
)
from .whisper import WhisperTranscriber

logger = logging.getLogger(__name__)


class TranscriptProcessingService:
    """Extract, normalize, segment, and chunk video transcripts.

    This service is designed for background workers as well as synchronous MVP
    endpoints. It does not persist to MongoDB or Qdrant directly; callers can
    persist ``segments`` and ``chunks`` after receiving the result.
    """

    def __init__(
        self,
        config: Optional[TranscriptProcessingConfig] = None,
        whisper_transcriber: Optional[WhisperTranscriber] = None,
    ) -> None:
        self.config = config or TranscriptProcessingConfig()
        self.whisper_transcriber = whisper_transcriber or WhisperTranscriber(self.config)

    def process(self, request: TranscriptExtractionRequest) -> TranscriptExtractionResult:
        """Run the full transcript pipeline for a video.

        Pipeline:
            1. Try platform captions/transcripts.
            2. If unavailable and enabled, run Whisper fallback.
            3. Normalize timestamped segments.
            4. Generate embedding-ready chunks while preserving timestamps.

        Returns a ``TranscriptExtractionResult`` even on expected failures so the
        caller can mark a single video as partial/unavailable while preserving the
        rest of the comparison.
        """
        logger.info(
            "Starting transcript processing",
            extra={"video_id": request.video_id, "platform": request.platform},
        )

        warnings: List[str] = []
        raw: Dict[str, Any] = {}

        try:
            segments, source_type, extractor_raw = self._extract_caption_segments(request)
            raw["caption_extractor"] = extractor_raw
        except TranscriptUnavailableError as exc:
            logger.info("Caption transcript unavailable: %s", exc)
            warnings.append(str(exc))
            segments = []
            source_type = TranscriptSource.UNKNOWN
        except Exception as exc:
            logger.warning("Caption extraction failed", exc_info=True)
            warnings.append(f"Caption extraction failed: {exc}")
            segments = []
            source_type = TranscriptSource.UNKNOWN

        if not segments and self.config.enable_whisper_fallback:
            try:
                logger.info("Attempting Whisper fallback for video_id=%s", request.video_id)
                segments = self.whisper_transcriber.transcribe_url(
                    request.source_url,
                    language=self.config.language or (request.preferred_languages[0] if request.preferred_languages else None),
                )
                source_type = TranscriptSource.WHISPER
            except Exception as exc:
                logger.error("Whisper fallback failed", exc_info=True)
                return TranscriptExtractionResult(
                    video_id=request.video_id,
                    status=TranscriptStatus.FAILED if not warnings else TranscriptStatus.UNAVAILABLE,
                    source_type=TranscriptSource.WHISPER,
                    error=f"Whisper fallback failed: {exc}",
                    warnings=warnings,
                    raw=raw,
                )

        if not segments:
            return TranscriptExtractionResult(
                video_id=request.video_id,
                status=TranscriptStatus.UNAVAILABLE,
                source_type=source_type,
                error="No transcript/captions were available for this video.",
                warnings=warnings,
                raw=raw,
            )

        normalized_segments = self._normalize_segments(segments, source_type=source_type)
        chunks = self.generate_chunks(normalized_segments, base_metadata=self._base_chunk_metadata(request))
        status = TranscriptStatus.READY if chunks else TranscriptStatus.PARTIAL

        logger.info(
            "Transcript processing complete",
            extra={
                "video_id": request.video_id,
                "segments": len(normalized_segments),
                "chunks": len(chunks),
                "source_type": source_type.value,
            },
        )
        return TranscriptExtractionResult(
            video_id=request.video_id,
            status=status,
            source_type=source_type,
            segments=normalized_segments,
            chunks=chunks,
            warnings=warnings,
            raw=raw,
        )

    def generate_chunks(
        self,
        segments: Sequence[TranscriptSegment],
        *,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TranscriptChunk]:
        """Create embedding-ready chunks from timestamped segments.

        The chunker favors timestamp boundaries over exact text length. It starts
        a new chunk when either the target duration or max text size is reached.
        A small overlap is added by replaying recent segments whose end timestamps
        sit within ``chunk_overlap_seconds`` of the previous boundary.
        """
        if not segments:
            return []

        chunks: List[TranscriptChunk] = []
        current: List[TranscriptSegment] = []
        chunk_start = segments[0].start_seconds

        for segment in segments:
            if not segment.text:
                continue

            projected = [*current, segment]
            projected_text = self._join_segment_text(projected)
            projected_duration = projected[-1].end_seconds - chunk_start

            should_flush = bool(current) and (
                projected_duration >= self.config.target_chunk_seconds
                or len(projected_text) > self.config.max_chunk_chars
            )

            if should_flush:
                chunks.append(self._build_chunk(len(chunks), current, base_metadata=base_metadata))
                current = self._overlap_tail(current)
                chunk_start = current[0].start_seconds if current else segment.start_seconds

            current.append(segment)

        if current:
            chunks.append(self._build_chunk(len(chunks), current, base_metadata=base_metadata))

        return chunks

    def _extract_caption_segments(
        self, request: TranscriptExtractionRequest
    ) -> tuple[List[TranscriptSegment], TranscriptSource, Dict[str, Any]]:
        """Extract captions using platform-specific strategies.

        YouTube gets a direct ``youtube-transcript-api`` path first. Other sources
        fall back to ``yt-dlp`` subtitle extraction because Instagram transcript
        availability varies and yt-dlp can expose subtitles when present.
        """
        platform = request.platform.lower().strip()
        if platform in {"youtube", "yt"}:
            try:
                return self._extract_youtube_transcript_api(request)
            except TranscriptUnavailableError:
                # Keep going to yt-dlp because it can sometimes find auto-captions
                # even when youtube-transcript-api does not.
                logger.info("youtube-transcript-api found no captions; trying yt-dlp subtitles")
            except Exception:
                logger.warning("youtube-transcript-api extraction failed; trying yt-dlp", exc_info=True)

        return self._extract_with_ytdlp_subtitles(request)

    def _extract_youtube_transcript_api(
        self, request: TranscriptExtractionRequest
    ) -> tuple[List[TranscriptSegment], TranscriptSource, Dict[str, Any]]:
        """Extract YouTube captions with youtube-transcript-api."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore[import-not-found]
            from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise TranscriptUnavailableError(
                "youtube-transcript-api is not installed; skipping direct YouTube transcript extraction."
            ) from exc

        video_id = request.platform_video_id or self._parse_youtube_id(request.source_url)
        if not video_id:
            raise TranscriptUnavailableError("Could not determine YouTube video ID for transcript extraction.")

        languages = request.preferred_languages or ["en"]
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            selected = None
            source_type = TranscriptSource.UNKNOWN
            try:
                selected = transcript_list.find_manually_created_transcript(languages)
                source_type = TranscriptSource.MANUAL_CAPTIONS
            except Exception:
                selected = transcript_list.find_generated_transcript(languages)
                source_type = TranscriptSource.AUTO_CAPTIONS

            fetched = selected.fetch()
        except (NoTranscriptFound, TranscriptsDisabled) as exc:
            raise TranscriptUnavailableError(f"No YouTube transcript available: {exc}") from exc
        except Exception as exc:
            raise TranscriptUnavailableError(f"YouTube transcript extraction failed: {exc}") from exc

        segments: List[TranscriptSegment] = []
        for index, item in enumerate(fetched):
            start = float(item.get("start") or 0.0)
            duration = float(item.get("duration") or 0.0)
            text = str(item.get("text") or "")
            if not text.strip():
                continue
            segments.append(
                TranscriptSegment(
                    segment_index=index,
                    text=text,
                    start_seconds=start,
                    end_seconds=start + duration,
                    source_type=source_type,
                    raw=dict(item),
                )
            )

        if not segments:
            raise TranscriptUnavailableError("YouTube transcript contained no usable text.")

        return segments, source_type, {"video_id": video_id, "languages": languages}

    def _extract_with_ytdlp_subtitles(
        self, request: TranscriptExtractionRequest
    ) -> tuple[List[TranscriptSegment], TranscriptSource, Dict[str, Any]]:
        """Extract subtitle files with yt-dlp and normalize them into segments."""
        try:
            import yt_dlp  # type: ignore[import-not-found]
        except Exception as exc:  # pragma: no cover - optional dependency
            raise TranscriptUnavailableError("yt-dlp is not installed; subtitle extraction unavailable.") from exc

        subtitle_dir = Path(self.config.temp_dir) / "subtitles"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(subtitle_dir / "%(id)s.%(ext)s")
        languages = request.preferred_languages or ["en"]

        ydl_opts: Dict[str, Any] = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": languages,
            "subtitlesformat": "vtt/srv3/best",
            "outtmpl": output_template,
            "quiet": True,
            "noplaylist": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(request.source_url, download=True)
        except Exception as exc:  # pragma: no cover - network/platform dependent
            raise TranscriptUnavailableError(f"yt-dlp subtitle extraction failed: {exc}") from exc

        native_id = str(info.get("id") or request.platform_video_id or "")
        subtitle_files = sorted(subtitle_dir.glob(f"{native_id}.*")) if native_id else []
        subtitle_files = [p for p in subtitle_files if p.suffix.lower() in {".vtt", ".srv3", ".ttml", ".json3"}]

        if not subtitle_files:
            raise TranscriptUnavailableError("yt-dlp found no subtitle files.")

        segments: List[TranscriptSegment] = []
        for file_path in subtitle_files:
            try:
                segments = self._parse_subtitle_file(file_path, TranscriptSource.YT_DLP_CAPTIONS)
                if segments:
                    break
            finally:
                try:
                    file_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to remove subtitle file: %s", file_path, exc_info=True)

        if not segments:
            raise TranscriptUnavailableError("Subtitle files existed but had no usable transcript text.")

        return segments, TranscriptSource.YT_DLP_CAPTIONS, {"platform_id": native_id, "languages": languages}

    def _parse_subtitle_file(self, path: Path, source_type: TranscriptSource) -> List[TranscriptSegment]:
        """Parse common subtitle formats produced by yt-dlp.

        VTT is the primary path. JSON3 and XML-like subtitle formats are handled
        best-effort so demos remain resilient across extractor output variants.
        """
        text = path.read_text(encoding="utf-8", errors="ignore")
        suffix = path.suffix.lower()
        if suffix == ".json3":
            return self._parse_json3_subtitles(text, source_type)
        return self._parse_vtt_like_subtitles(text, source_type)

    def _parse_vtt_like_subtitles(self, content: str, source_type: TranscriptSource) -> List[TranscriptSegment]:
        """Parse WebVTT-style subtitles into normalized segments."""
        segments: List[TranscriptSegment] = []
        blocks = re.split(r"\n\s*\n", content.replace("\r\n", "\n"))
        timestamp_pattern = re.compile(r"(?P<start>[\d:.]+)\s+-->\s+(?P<end>[\d:.]+)")

        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            time_line_index = next((i for i, line in enumerate(lines) if "-->" in line), -1)
            if time_line_index < 0:
                continue
            match = timestamp_pattern.search(lines[time_line_index])
            if not match:
                continue
            caption_lines = lines[time_line_index + 1 :]
            caption_text = self._clean_caption_text(" ".join(caption_lines))
            if not caption_text:
                continue
            segments.append(
                TranscriptSegment(
                    segment_index=len(segments),
                    text=caption_text,
                    start_seconds=self._timestamp_to_seconds(match.group("start")),
                    end_seconds=self._timestamp_to_seconds(match.group("end")),
                    source_type=source_type,
                )
            )
        return segments

    def _parse_json3_subtitles(self, content: str, source_type: TranscriptSource) -> List[TranscriptSegment]:
        """Parse YouTube JSON3 subtitle payloads produced by yt-dlp."""
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return []

        segments: List[TranscriptSegment] = []
        for event in payload.get("events", []):
            parts = event.get("segs") or []
            text = self._clean_caption_text("".join(str(part.get("utf8") or "") for part in parts))
            if not text:
                continue
            start_ms = float(event.get("tStartMs") or 0.0)
            duration_ms = float(event.get("dDurationMs") or 0.0)
            segments.append(
                TranscriptSegment(
                    segment_index=len(segments),
                    text=text,
                    start_seconds=start_ms / 1000.0,
                    end_seconds=(start_ms + duration_ms) / 1000.0,
                    source_type=source_type,
                    raw=event,
                )
            )
        return segments

    def _normalize_segments(
        self,
        segments: Iterable[TranscriptSegment],
        *,
        source_type: TranscriptSource,
    ) -> List[TranscriptSegment]:
        """Sort, de-duplicate, and validate transcript segments."""
        normalized: List[TranscriptSegment] = []
        previous_key: Optional[tuple[float, str]] = None

        for segment in sorted(segments, key=lambda item: (item.start_seconds, item.end_seconds)):
            clean_text = self._clean_caption_text(segment.text)
            if not clean_text:
                continue
            key = (round(segment.start_seconds, 2), clean_text)
            if key == previous_key:
                continue
            previous_key = key
            normalized.append(
                TranscriptSegment(
                    segment_index=len(normalized),
                    text=clean_text,
                    start_seconds=segment.start_seconds,
                    end_seconds=max(segment.end_seconds, segment.start_seconds + 0.01),
                    source_type=segment.source_type or source_type,
                    confidence=segment.confidence,
                    raw=segment.raw,
                )
            )
        return normalized

    def _build_chunk(
        self,
        chunk_index: int,
        segments: Sequence[TranscriptSegment],
        *,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> TranscriptChunk:
        """Build one chunk and attach stable source metadata."""
        text = self._join_segment_text(segments)
        start_seconds = segments[0].start_seconds
        end_seconds = segments[-1].end_seconds
        source_type = segments[0].source_type if segments else TranscriptSource.UNKNOWN
        metadata = dict(base_metadata or {})
        metadata.update(
            {
                "chunk_index": chunk_index,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "source_type": source_type.value,
            }
        )
        return TranscriptChunk(
            chunk_index=chunk_index,
            text=text,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            segment_indices=[segment.segment_index for segment in segments],
            source_type=source_type,
            metadata=metadata,
        )

    def _overlap_tail(self, segments: Sequence[TranscriptSegment]) -> List[TranscriptSegment]:
        """Return recent segments to seed the next chunk overlap."""
        if not segments or self.config.chunk_overlap_seconds <= 0:
            return []
        boundary = segments[-1].end_seconds - self.config.chunk_overlap_seconds
        return [segment for segment in segments if segment.end_seconds >= boundary]

    @staticmethod
    def _join_segment_text(segments: Sequence[TranscriptSegment]) -> str:
        """Join segment text into a single embedding payload."""
        return " ".join(segment.text for segment in segments if segment.text).strip()

    @staticmethod
    def _clean_caption_text(text: str) -> str:
        """Remove common caption markup and normalize whitespace."""
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"\[[^\]]{1,40}\]", " ", text)  # e.g. [Music]
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _timestamp_to_seconds(value: str) -> float:
        """Convert VTT timestamps (HH:MM:SS.mmm or MM:SS.mmm) to seconds."""
        parts = value.strip().split(":")
        try:
            numeric = [float(part) for part in parts]
        except ValueError:
            return 0.0
        if len(numeric) == 3:
            hours, minutes, seconds = numeric
            return hours * 3600 + minutes * 60 + seconds
        if len(numeric) == 2:
            minutes, seconds = numeric
            return minutes * 60 + seconds
        return numeric[0] if numeric else 0.0

    @staticmethod
    def _parse_youtube_id(url: str) -> Optional[str]:
        """Extract a YouTube video ID from common URL shapes."""
        patterns = [
            r"youtu\.be/(?P<id>[A-Za-z0-9_-]{6,})",
            r"youtube\.com/watch\?[^#]*v=(?P<id>[A-Za-z0-9_-]{6,})",
            r"youtube\.com/shorts/(?P<id>[A-Za-z0-9_-]{6,})",
            r"youtube\.com/embed/(?P<id>[A-Za-z0-9_-]{6,})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group("id")
        return None

    @staticmethod
    def _base_chunk_metadata(request: TranscriptExtractionRequest) -> Dict[str, Any]:
        """Return metadata expected by the vector-storage layer."""
        return {
            "video_id": request.video_id,
            "platform": request.platform,
            "source_url": request.source_url,
            "platform_video_id": request.platform_video_id,
            **request.metadata,
        }
