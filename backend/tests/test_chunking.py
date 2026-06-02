import pytest

from app.modules.chunking import ChunkingRequest, TranscriptChunkingService, TranscriptSegment


def _segment(segment_index: int, words: list[str], start: float, end: float) -> TranscriptSegment:
    return TranscriptSegment(
        segment_index=segment_index,
        text=" ".join(words),
        start_seconds=start,
        end_seconds=end,
        source_type="manual_caption",
    )


def test_chunking_uses_default_size_and_overlap() -> None:
    words = [f"w{i}" for i in range(900)]
    request = ChunkingRequest(
        comparison_id="cmp_1",
        video_id="A",
        platform="youtube",
        source_url="https://youtube.com/watch?v=test",
        creator="@creator",
        segments=[_segment(0, words, 0.0, 90.0)],
    )

    result = TranscriptChunkingService().chunk_transcript(request)

    assert result.chunk_size == 500
    assert result.overlap == 100
    assert result.total_chunks == 2
    assert result.chunks[0].metadata.token_count == 500
    assert result.chunks[1].metadata.token_count == 500

    first_tokens = result.chunks[0].text.split()
    second_tokens = result.chunks[1].text.split()
    assert first_tokens[-100:] == second_tokens[:100]


def test_chunk_metadata_preserves_source_fields_and_timestamps() -> None:
    request = ChunkingRequest(
        comparison_id="cmp_2",
        video_id="B",
        platform="instagram",
        source_url="https://instagram.com/reel/test",
        creator="@reel_creator",
        segments=[
            _segment(0, ["hook", "starts", "fast"], 0.0, 3.0),
            _segment(1, ["payoff", "lands", "here"], 3.0, 6.5),
        ],
        chunk_size=10,
        overlap=2,
        metadata_extra={"platform_video_id": "abc123"},
    )

    result = TranscriptChunkingService().chunk_transcript(request)
    chunk = result.chunks[0]
    payload = chunk.metadata.to_payload()

    assert result.total_chunks == 1
    assert chunk.metadata.comparison_id == "cmp_2"
    assert chunk.metadata.video_id == "B"
    assert chunk.metadata.platform == "instagram"
    assert chunk.metadata.creator == "@reel_creator"
    assert chunk.metadata.start_seconds == 0.0
    assert chunk.metadata.end_seconds == 6.5
    assert chunk.metadata.segment_start_index == 0
    assert chunk.metadata.segment_end_index == 1
    assert chunk.metadata.source_segment_indices == [0, 1]
    assert payload["platform_video_id"] == "abc123"


def test_chunk_ids_are_deterministic_for_same_input() -> None:
    request = ChunkingRequest(
        comparison_id="cmp_3",
        video_id="A",
        segments=[_segment(0, [f"w{i}" for i in range(600)], 0.0, 60.0)],
    )
    service = TranscriptChunkingService()

    first = service.chunk_transcript(request)
    second = service.chunk_transcript(request)

    assert [chunk.metadata.chunk_id for chunk in first.chunks] == [
        chunk.metadata.chunk_id for chunk in second.chunks
    ]


def test_segments_are_sorted_before_chunking() -> None:
    request = ChunkingRequest(
        video_id="A",
        segments=[
            _segment(1, ["second"], 5.0, 6.0),
            _segment(0, ["first"], 0.0, 1.0),
        ],
        chunk_size=10,
        overlap=2,
    )

    result = TranscriptChunkingService().chunk_transcript(request)

    assert result.chunks[0].text == "first second"
    assert result.chunks[0].metadata.start_seconds == 0.0
    assert result.chunks[0].metadata.end_seconds == 6.0


def test_request_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError, match="overlap must be smaller"):
        ChunkingRequest(
            video_id="A",
            segments=[_segment(0, ["hello"], 0.0, 1.0)],
            chunk_size=100,
            overlap=100,
        )


def test_segment_rejects_invalid_timestamp_order() -> None:
    with pytest.raises(ValueError, match="end_seconds cannot be earlier"):
        TranscriptSegment(
            segment_index=0,
            text="bad timestamp",
            start_seconds=10.0,
            end_seconds=9.0,
        )
