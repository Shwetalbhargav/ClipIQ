from __future__ import annotations

import pytest

from app.modules.comparisons.service import ChatServiceStreamer
from app.modules.graph.nodes import GraphDependencies


class ExplodingChatService:
    async def chat(self, payload):
        raise AssertionError("production streaming should not call full chat_service.chat() first")


class FakeMemoryRepo:
    def __init__(self) -> None:
        self.persisted = []

    async def get_recent_messages(self, *, comparison_id, limit=6):
        return [{"role": "user", "content": "Earlier context"}]

    async def append_message(self, *, comparison_id, role, content):
        self.persisted.append({"comparison_id": comparison_id, "role": role, "content": content})


class FakeRetriever:
    async def retrieve(self, *, comparison_id, video_id, query, top_k):
        return [
            {
                "chunk_id": f"{video_id}-0",
                "comparison_id": comparison_id,
                "video_id": video_id,
                "platform": "youtube" if video_id == "A" else "instagram",
                "source_url": f"https://example.com/{video_id}",
                "creator": f"creator-{video_id}",
                "chunk_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "text": f"Video {video_id} hook evidence.",
                "score": 0.9,
            }
        ]


class FakeMetadataRepo:
    async def get_video_metadata(self, *, comparison_id):
        return {
            "A": {
                "video_id": "A",
                "platform": "youtube",
                "creator": "creator-A",
                "views": 1000,
                "likes": 100,
                "comments": 25,
                "follower_count": 10_000,
                "hashtags": ["demo"],
                "engagement_rate": 12.5,
            },
            "B": {
                "video_id": "B",
                "platform": "instagram",
                "creator": "creator-B",
                "views": 1000,
                "likes": 50,
                "comments": 10,
                "follower_count": 8_000,
                "hashtags": ["demo"],
                "engagement_rate": 6.0,
            },
        }


class FakeGenerator:
    async def generate(self, **kwargs):
        return "unused"


class FakeDelta:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeChoice:
    def __init__(self, content: str) -> None:
        self.delta = FakeDelta(content)


class FakeChunk:
    def __init__(self, content: str) -> None:
        self.choices = [FakeChoice(content)]


class FakeOpenAIStream:
    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    async def __aiter__(self):
        for token in self.tokens:
            yield FakeChunk(token)


class FakeCompletions:
    async def create(self, **kwargs):
        assert kwargs["stream"] is True
        return FakeOpenAIStream(["real ", "token ", "stream"])


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeOpenAI:
    def __init__(self) -> None:
        self.chat = FakeChat()


@pytest.mark.asyncio
async def test_chat_service_streamer_uses_true_model_streaming_path() -> None:
    memory_repo = FakeMemoryRepo()
    deps = GraphDependencies(
        retriever=FakeRetriever(),
        metadata_repo=FakeMetadataRepo(),
        memory_repo=memory_repo,
        response_generator=FakeGenerator(),
        top_k_per_video=1,
    )
    streamer = ChatServiceStreamer(ExplodingChatService(), graph_deps=deps, api_key="", model="test-model")
    streamer.openai = FakeOpenAI()

    items = [
        item
        async for item in streamer.stream_chat(
            comparison_id="cmp-1",
            message="Why did A win?",
            response_id="resp-1",
        )
    ]

    assert items[:3] == ["real ", "token ", "stream"]
    assert any(isinstance(item, dict) and item["type"] == "citation" for item in items)
    assert [item["role"] for item in memory_repo.persisted] == ["user", "assistant"]
    assert memory_repo.persisted[-1]["content"] == "real token stream"
