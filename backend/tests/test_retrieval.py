"""Tests for Module 5: retrieval.

These tests keep the retrieval layer isolated from external services. A fake
vector client stands in for Qdrant/Chroma, and a deterministic embedding
function stands in for the real embedding provider.
"""

from __future__ import annotations

import asyncio
from typing import Any, Sequence

import pytest
from pydantic import ValidationError

from app.modules.retrieval.citation import (
    build_citation_id,
    build_citation_label,
    format_timestamp,
    normalize_excerpt,
)
from app.modules.retrieval.schema import RetrievalFilter, RetrievalRequest, RetrievedChunk
from app.modules.retrieval.service import RetrievalService, build_metadata_filter, point_to_chunk


class FakeVectorClient:
    """Tiny in-memory vector client used to assert service behavior."""

    def __init__(self, points: Sequence[dict[str, Any]]) -> None:
        self.points = list(points)
        self.last_call: dict[str, Any] | None = None

    async def search(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
        filters: dict[str, Any],
        score_threshold: float | None = None,
    ) -> Sequence[dict[str, Any]]:
        self.last_call = {
            "vector": list(vector),
            "top_k": top_k,
            "filters": filters,
            "score_threshold": score_threshold,
        }

        # Simulate adapter-side metadata filtering and top-k slicing.
        filtered = []
        for point in self.points:
            payload = point["payload"]
            if all(payload.get(key) == value for key, value in filters.items()):
                filtered.append(point)

        if score_threshold is not None:
            filtered = [point for point in filtered if point.get("score", 0.0) >= score_threshold]

        return sorted(filtered, key=lambda point: point["score"], reverse=True)[:top_k]


async def fake_embed_query(query: str) -> list[float]:
    """Deterministic embedding stub; enough to verify the query is embedded."""

    return [float(len(query)), 1.0, 0.5]


def make_point(
    *,
    point_id: str,
    comparison_id: str = "cmp_123",
    video_id: str = "video_a",
    video_label: str = "A",
    platform: str = "youtube",
    chunk_index: int = 3,
    score: float = 0.91,
    text: str = "Strong opening hook with a clear promise in the first five seconds.",
) -> dict[str, Any]:
    return {
        "id": point_id,
        "score": score,
        "payload": {
            "comparison_id": comparison_id,
            "video_id": video_id,
            "video_label": video_label,
            "platform": platform,
            "source_url": f"https://example.com/{point_id}",
            "creator": "@creator",
            "chunk_id": f"chunk_{point_id}",
            "chunk_index": chunk_index,
            "start_seconds": 5,
            "end_seconds": 12,
            "title": "Example video",
            "text": text,
            "raw_provider": "test-fixture",
        },
    }


def test_build_metadata_filter_keeps_required_comparison_scope() -> None:
    filters = RetrievalFilter(
        comparison_id="cmp_123",
        video_label="A",
        platform="YouTube",
        creator="@creator",
    )

    assert build_metadata_filter(filters) == {
        "comparison_id": "cmp_123",
        "video_label": "A",
        "platform": "youtube",
        "creator": "@creator",
    }


def test_retrieval_request_rejects_blank_query() -> None:
    with pytest.raises(ValidationError):
        RetrievalRequest(query="   ", filters=RetrievalFilter(comparison_id="cmp_123"))


def test_retrieval_request_limits_top_k() -> None:
    with pytest.raises(ValidationError):
        RetrievalRequest(query="hooks", filters=RetrievalFilter(comparison_id="cmp_123"), top_k=25)


def test_point_to_chunk_normalizes_payload_and_extra_metadata() -> None:
    chunk = point_to_chunk(make_point(point_id="p1"))

    assert isinstance(chunk, RetrievedChunk)
    assert chunk.id == "p1"
    assert chunk.score == pytest.approx(0.91)
    assert chunk.metadata.comparison_id == "cmp_123"
    assert chunk.metadata.video_label == "A"
    assert chunk.metadata.platform == "youtube"
    assert chunk.metadata.chunk_index == 3
    assert chunk.metadata.start_seconds == pytest.approx(5.0)
    assert chunk.metadata.end_seconds == pytest.approx(12.0)
    assert chunk.metadata.extra == {"raw_provider": "test-fixture"}


def test_point_to_chunk_supports_start_time_aliases() -> None:
    point = make_point(point_id="p2")
    payload = point["payload"]
    payload.pop("start_seconds")
    payload.pop("end_seconds")
    payload["start_time"] = 1.5
    payload["end_time"] = 4.25

    chunk = point_to_chunk(point)

    assert chunk.metadata.start_seconds == pytest.approx(1.5)
    assert chunk.metadata.end_seconds == pytest.approx(4.25)


def test_citation_helpers_create_readable_and_stable_output() -> None:
    chunk = point_to_chunk(make_point(point_id="p1"))

    assert format_timestamp(65.9) == "1:05"
    assert build_citation_label(chunk) == "Video A · Chunk 3 · 0:05-0:12"
    assert build_citation_id(chunk) == build_citation_id(chunk)

    long_text = "word " * 100
    excerpt = normalize_excerpt(long_text, max_chars=40)
    assert len(excerpt) <= 40
    assert excerpt.endswith("…")


def test_retrieval_service_returns_top_k_chunks_and_matching_citations() -> None:
    points = [
        make_point(point_id="high", score=0.95, video_label="A"),
        make_point(point_id="low", score=0.70, video_label="A"),
        make_point(point_id="wrong_video", score=0.99, video_label="B", video_id="video_b"),
    ]
    vector_client = FakeVectorClient(points)
    service = RetrievalService(vector_client=vector_client, embed_query=fake_embed_query)
    request = RetrievalRequest(
        query="Compare the hooks in the first five seconds",
        filters=RetrievalFilter(comparison_id="cmp_123", video_label="A"),
        top_k=1,
    )

    result = asyncio.run(service.retrieve(request))

    assert result.has_sources is True
    assert [chunk.id for chunk in result.chunks] == ["high"]
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "chunk_high"
    assert result.citations[0].label == "Video A · Chunk 3 · 0:05-0:12"
    assert vector_client.last_call == {
        "vector": [float(len(request.query)), 1.0, 0.5],
        "top_k": 1,
        "filters": {"comparison_id": "cmp_123", "video_label": "A"},
        "score_threshold": None,
    }


def test_retrieval_service_applies_score_threshold() -> None:
    points = [
        make_point(point_id="keep", score=0.80),
        make_point(point_id="drop", score=0.30),
    ]
    service = RetrievalService(vector_client=FakeVectorClient(points), embed_query=fake_embed_query)
    request = RetrievalRequest(
        query="What worked?",
        filters=RetrievalFilter(comparison_id="cmp_123"),
        top_k=5,
        score_threshold=0.5,
    )

    result = asyncio.run(service.retrieve(request))

    assert [chunk.id for chunk in result.chunks] == ["keep"]
    assert [citation.chunk_id for citation in result.citations] == ["chunk_keep"]


def test_retrieval_service_returns_empty_result_when_no_chunks_match() -> None:
    service = RetrievalService(
        vector_client=FakeVectorClient([make_point(point_id="other", comparison_id="cmp_other")]),
        embed_query=fake_embed_query,
    )
    request = RetrievalRequest(query="Any evidence?", filters=RetrievalFilter(comparison_id="cmp_123"))

    result = asyncio.run(service.retrieve(request))

    assert result.has_sources is False
    assert result.chunks == []
    assert result.citations == []
