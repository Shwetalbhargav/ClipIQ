"""Tests for the ClipIQ transcript processing module.

The tests avoid real network calls, YouTube requests, media downloads, and local
Whisper model loading. Instead, they exercise the module's deterministic business
logic and mock extractor boundaries so CI stays fast and reliable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.transcript_processing import (
    TranscriptExtractionRequest,
    TranscriptProcessingConfig,
    TranscriptProcessingService,
    TranscriptSegment,
    TranscriptSource,
    TranscriptStatus,
    TranscriptUnavailableError,
)


@pytest.fixture()
def extraction_request() -> TranscriptExtractionRequest:
    """Return a reusable extraction request for Video A."""
    return TranscriptExtractionRequest(
        video_id="A",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        platform="youtube",
        platform_video_id="dQw4w9WgXcQ",
        metadata={"comparison_id": "cmp_123", "creator": "demo_creator"},
    )


def make_segment(index: int, text: str, start: float, end: float) -> TranscriptSegment:
    """Create a normalized manual-caption segment for tests."""
    return TranscriptSegment(
        segment_index=index,
        text=text,
        start_seconds=start,
        end_seconds=end,
        source_type=TranscriptSource.MANUAL_CAPTIONS,
    )


def test_process_uses_caption_segments_and_generates_timestamped_chunks(monkeypatch, extraction_request):
    """Caption-first extraction should produce ready chunks with source metadata."""
    service = TranscriptProcessingService(
        TranscriptProcessingConfig(
            enable_whisper_fallback=False,
            target_chunk_seconds=6,
            max_chunk_chars=200,
            chunk_overlap_seconds=0,
        )
    )
    caption_segments = [
        make_segment(0, "Here is the hook", 0.0, 2.0),
        make_segment(1, "then the creator adds context", 2.0, 5.2),
        make_segment(2, "and ends with a payoff", 5.2, 8.0),
    ]

    def fake_extract(_request):
        return caption_segments, TranscriptSource.MANUAL_CAPTIONS, {"extractor": "fake"}

    monkeypatch.setattr(service, "_extract_caption_segments", fake_extract)

    result = service.process(extraction_request)

    assert result.status == TranscriptStatus.READY
    assert result.source_type == TranscriptSource.MANUAL_CAPTIONS
    assert result.error is None
    assert result.transcript_text == "Here is the hook then the creator adds context and ends with a payoff"
    assert len(result.segments) == 3
    assert len(result.chunks) == 2
    assert result.chunks[0].start_seconds == pytest.approx(0.0)
    assert result.chunks[0].end_seconds == pytest.approx(5.2)
    assert result.chunks[0].metadata["video_id"] == "A"
    assert result.chunks[0].metadata["comparison_id"] == "cmp_123"
    assert result.chunks[0].metadata["creator"] == "demo_creator"


def test_generate_chunks_preserves_overlap_and_segment_indices():
    """Chunk generation should keep timestamps and repeat boundary context."""
    service = TranscriptProcessingService(
        TranscriptProcessingConfig(
            target_chunk_seconds=4,
            max_chunk_chars=500,
            chunk_overlap_seconds=2,
            enable_whisper_fallback=False,
        )
    )
    segments = [
        make_segment(0, "zero", 0.0, 1.0),
        make_segment(1, "one", 1.0, 3.0),
        make_segment(2, "two", 3.0, 5.0),
        make_segment(3, "three", 5.0, 7.0),
    ]

    chunks = service.generate_chunks(segments, base_metadata={"video_id": "B"})

    assert len(chunks) == 3
    assert chunks[0].segment_indices == [0, 1]
    assert chunks[1].segment_indices == [0, 1, 2]
    assert chunks[2].segment_indices == [1, 2, 3]
    assert chunks[2].start_seconds == pytest.approx(1.0)
    assert chunks[2].metadata["video_id"] == "B"
    assert chunks[2].metadata["chunk_index"] == 2


def test_process_returns_unavailable_when_captions_missing_and_whisper_disabled(monkeypatch, extraction_request):
    """Expected transcript misses should return a safe result, not raise."""
    service = TranscriptProcessingService(
        TranscriptProcessingConfig(enable_whisper_fallback=False)
    )

    def missing_captions(_request):
        raise TranscriptUnavailableError("no captions")

    monkeypatch.setattr(service, "_extract_caption_segments", missing_captions)

    result = service.process(extraction_request)

    assert result.status == TranscriptStatus.UNAVAILABLE
    assert result.source_type == TranscriptSource.UNKNOWN
    assert result.segments == []
    assert result.chunks == []
    assert "No transcript" in result.error
    assert result.warnings == ["no captions"]


def test_process_falls_back_to_whisper_when_captions_are_missing(monkeypatch, extraction_request):
    """Whisper fallback should be used only after caption extraction misses."""
    service = TranscriptProcessingService(
        TranscriptProcessingConfig(
            enable_whisper_fallback=True,
            target_chunk_seconds=30,
        )
    )

    def missing_captions(_request):
        raise TranscriptUnavailableError("captions unavailable")

    def fake_whisper(source_url: str, *, language: str | None = None):
        assert source_url == extraction_request.source_url
        assert language == "en"
        return [
            TranscriptSegment(
                segment_index=0,
                text="whisper generated transcript",
                start_seconds=0.0,
                end_seconds=3.5,
                source_type=TranscriptSource.WHISPER,
            )
        ]

    monkeypatch.setattr(service, "_extract_caption_segments", missing_captions)
    monkeypatch.setattr(service.whisper_transcriber, "transcribe_url", fake_whisper)

    result = service.process(extraction_request)

    assert result.status == TranscriptStatus.READY
    assert result.source_type == TranscriptSource.WHISPER
    assert result.segments[0].source_type == TranscriptSource.WHISPER
    assert result.chunks[0].text == "whisper generated transcript"
    assert result.warnings == ["captions unavailable"]


def test_vtt_and_json3_parsers_keep_timestamps(tmp_path: Path):
    """Subtitle parsers should convert provider formats into timestamped segments."""
    service = TranscriptProcessingService(
        TranscriptProcessingConfig(enable_whisper_fallback=False)
    )
    vtt_file = tmp_path / "captions.vtt"
    vtt_file.write_text(
        "WEBVTT\n\n"
        "00:00:00.000 --> 00:00:02.500\n"
        "<v Speaker>First [Music] line</v>\n\n"
        "00:00:02.500 --> 00:00:05.000\n"
        "Second &amp; stronger line\n",
        encoding="utf-8",
    )

    vtt_segments = service._parse_subtitle_file(vtt_file, TranscriptSource.YT_DLP_CAPTIONS)

    assert [segment.text for segment in vtt_segments] == ["First line", "Second & stronger line"]
    assert vtt_segments[0].start_seconds == pytest.approx(0.0)
    assert vtt_segments[0].end_seconds == pytest.approx(2.5)

    json3_file = tmp_path / "captions.json3"
    json3_file.write_text(
        '{"events":[{"tStartMs":1200,"dDurationMs":800,"segs":[{"utf8":"JSON caption"}]}]}',
        encoding="utf-8",
    )

    json_segments = service._parse_subtitle_file(json3_file, TranscriptSource.YT_DLP_CAPTIONS)

    assert json_segments[0].text == "JSON caption"
    assert json_segments[0].start_seconds == pytest.approx(1.2)
    assert json_segments[0].end_seconds == pytest.approx(2.0)


def test_youtube_id_parser_supports_common_url_shapes():
    """YouTube video IDs are needed for direct transcript-api extraction."""
    parse = TranscriptProcessingService._parse_youtube_id

    assert parse("https://youtu.be/abcDEF_1234") == "abcDEF_1234"
    assert parse("https://www.youtube.com/watch?v=abcDEF_1234&t=5s") == "abcDEF_1234"
    assert parse("https://www.youtube.com/shorts/abcDEF_1234") == "abcDEF_1234"
    assert parse("https://example.com/video/abcDEF_1234") is None
