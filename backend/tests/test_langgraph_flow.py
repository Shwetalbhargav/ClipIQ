"""Tests for Module 10 LangGraph workflow.

These tests use fake adapters so they run quickly and do not require MongoDB,
Qdrant, OpenAI, or network access. They verify the graph retrieves both videos,
fetches metadata, compares engagement, builds citations, generates an answer,
and persists the chat turn.
"""

from __future__ import annotations

import pytest

from app.modules.graph.nodes import GraphDependencies
from app.modules.graph.workflow import run_graph


class FakeRetriever:
    def __init__(self) -> None:
        self.calls = []

    async def retrieve(self, *, comparison_id, video_id, query, top_k):
        self.calls.append(
            {
                "comparison_id": comparison_id,
                "video_id": video_id,
                "query": query,
                "top_k": top_k,
            }
        )
        return [
            {
                "chunk_id": f"chunk-{video_id}-0",
                "comparison_id": comparison_id,
                "video_id": video_id,
                "platform": "youtube" if video_id == "A" else "instagram",
                "source_url": f"https://example.com/{video_id}",
                "creator": f"creator-{video_id}",
                "chunk_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "text": f"Video {video_id} opens with a strong hook and clear payoff.",
                "score": 0.91,
            }
        ]


class FakeMetadataRepo:
    async def get_video_metadata(self, *, comparison_id):
        return {
            "A": {
                "video_id": "A",
                "platform": "youtube",
                "source_url": "https://example.com/A",
                "creator": "creator-A",
                "title": "Video A",
                "views": 1000,
                "likes": 120,
                "comments": 30,
                "follower_count": 50000,
                "hashtags": ["demo", "growth"],
                "engagement_rate": 15.0,
                "engagement_formula": "((likes + comments) / views) * 100",
                "duration_seconds": 30,
                "transcript_status": "available",
            },
            "B": {
                "video_id": "B",
                "platform": "instagram",
                "source_url": "https://example.com/B",
                "creator": "creator-B",
                "title": "Video B",
                "views": 2000,
                "likes": 100,
                "comments": 20,
                "follower_count": 75000,
                "hashtags": ["demo"],
                "engagement_rate": 6.0,
                "engagement_formula": "((likes + comments) / views) * 100",
                "duration_seconds": 28,
                "transcript_status": "available",
            },
        }


class FakeMemoryRepo:
    def __init__(self) -> None:
        self.persisted = []

    async def get_recent_messages(self, *, comparison_id, limit=6):
        return [{"role": "user", "content": "Earlier, we cared about hooks."}]

    async def append_message(self, *, comparison_id, role, content):
        self.persisted.append(
            {"comparison_id": comparison_id, "role": role, "content": content}
        )


class FakeGenerator:
    def __init__(self) -> None:
        self.received = None

    async def generate(self, *, question, context, memory):
        self.received = {"question": question, "context": context, "memory": memory}
        assert "STRUCTURED METADATA" in context
        assert "Video A Chunk 0" in context
        assert "Video B Chunk 0" in context
        return "Video A likely performed better because its hook evidence is stronger [Video A Chunk 0]."


@pytest.mark.asyncio
async def test_langgraph_flow_retrieves_compares_generates_and_persists():
    retriever = FakeRetriever()
    memory_repo = FakeMemoryRepo()
    generator = FakeGenerator()
    deps = GraphDependencies(
        retriever=retriever,
        metadata_repo=FakeMetadataRepo(),
        memory_repo=memory_repo,
        response_generator=generator,
        top_k_per_video=3,
    )

    result = await run_graph(
        deps,
        comparison_id="cmp-123",
        question="Why did Video A get more engagement than Video B?",
    )

    assert [call["video_id"] for call in retriever.calls] == ["A", "B"]
    assert all(call["comparison_id"] == "cmp-123" for call in retriever.calls)
    assert all(call["top_k"] == 3 for call in retriever.calls)

    assert result["comparison"]["winner_by_engagement_rate"] == "A"
    assert result["comparison"]["engagement_rate_delta"] == 9.0
    assert result["answer"].startswith("Video A likely performed better")
    assert {c["citation_id"] for c in result["citations"]} == {
        "Video A Chunk 0",
        "Video B Chunk 0",
    }

    assert generator.received is not None
    assert generator.received["memory"] == [
        {"role": "user", "content": "Earlier, we cared about hooks."}
    ]
    assert [item["role"] for item in memory_repo.persisted] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_langgraph_flow_handles_missing_engagement_rate_without_fabricating():
    class MissingRateMetadataRepo(FakeMetadataRepo):
        async def get_video_metadata(self, *, comparison_id):
            metadata = await super().get_video_metadata(comparison_id=comparison_id)
            metadata["B"]["engagement_rate"] = None
            metadata["B"]["views"] = None
            return metadata

    deps = GraphDependencies(
        retriever=FakeRetriever(),
        metadata_repo=MissingRateMetadataRepo(),
        memory_repo=FakeMemoryRepo(),
        response_generator=FakeGenerator(),
    )

    result = await run_graph(
        deps,
        comparison_id="cmp-missing",
        question="What's the engagement rate of each?",
    )

    assert result["comparison"]["winner_by_engagement_rate"] is None
    assert result["comparison"]["engagement_rate_delta"] is None
    assert "unavailable" in result["context"]
    assert result["comparison"]["metadata_notes"] == [
        "Engagement-rate comparison is limited because one or both rates are unavailable."
    ]
