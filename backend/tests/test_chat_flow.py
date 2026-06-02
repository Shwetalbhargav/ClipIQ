"""Tests for Module 7 chat flow.

These tests use deterministic fakes so CI does not require OpenAI, LangGraph,
MongoDB, Qdrant, or Chroma credentials. The goal is to prove the endpoint
orchestrates session memory, retrieval, graph invocation, and citations.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.modules.chat.router import router
from app.modules.chat.schema import ChatMessage, ChatRole, RetrievedChunk
from app.modules.chat.service import ChatService


class FakeMemoryStore:
    def __init__(self) -> None:
        self.messages: dict[str, list[ChatMessage]] = {}

    async def get_messages(self, session_id: str, *, limit: int = 6) -> list[ChatMessage]:
        return self.messages.get(session_id, [])[-limit:]

    async def append_message(self, session_id: str, message: ChatMessage) -> None:
        self.messages.setdefault(session_id, []).append(message)


class FakeRetriever:
    def __init__(self) -> None:
        self.last_call: dict | None = None

    async def retrieve(self, *, session_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        self.last_call = {"session_id": session_id, "query": query, "top_k": top_k}
        return [
            RetrievedChunk(
                chunk_id="chunk-A-0",
                video_id="A",
                chunk_index=0,
                text="Video A opens with a direct pain-point hook in the first five seconds.",
                platform="youtube",
                start_seconds=0,
                end_seconds=5,
                score=0.91,
            ),
            RetrievedChunk(
                chunk_id="chunk-B-0",
                video_id="B",
                chunk_index=0,
                text="Video B starts slower and delays the payoff until after the intro.",
                platform="instagram",
                start_seconds=0,
                end_seconds=5,
                score=0.87,
            ),
        ]


class FakeComparisonRepository:
    async def get_comparison_context(self, session_id: str):
        if session_id == "missing-session":
            return None
        return {
            "session_id": session_id,
            "videos": {
                "A": {"creator": "creator_a", "engagement_rate": 7.2},
                "B": {"creator": "creator_b", "engagement_rate": 3.1},
            },
        }


class FakeGraphRunner:
    def __init__(self) -> None:
        self.last_state: dict | None = None

    async def ainvoke(self, state: dict):
        self.last_state = state
        return {
            "answer": "Video A likely performed better because it states the payoff earlier than Video B.",
            "citations": [
                {
                    "label": "Video A Chunk 0",
                    "video_id": "A",
                    "chunk_id": "chunk-A-0",
                    "chunk_index": 0,
                    "platform": "youtube",
                    "start_seconds": 0,
                    "end_seconds": 5,
                    "text": "Video A opens with a direct pain-point hook in the first five seconds.",
                    "score": 0.91,
                }
            ],
            "model": "test-graph",
            "usage": {"prompt_tokens": 10, "completion_tokens": 12},
        }


@pytest.fixture()
def chat_dependencies():
    memory = FakeMemoryStore()
    retriever = FakeRetriever()
    repository = FakeComparisonRepository()
    graph = FakeGraphRunner()
    service = ChatService(
        memory_store=memory,
        retriever=retriever,
        comparison_repository=repository,
        graph_runner=graph,
    )
    return service, memory, retriever, graph


@pytest.fixture()
def app(chat_dependencies):
    service, *_ = chat_dependencies
    app = FastAPI()
    app.state.chat_service = service
    app.include_router(router)
    return app


@pytest.mark.anyio
async def test_post_chat_runs_full_flow_and_returns_citations(app, chat_dependencies):
    service, memory, retriever, graph = chat_dependencies

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "session_id": "session-123",
                "message": "Compare the hooks in the first 5 seconds.",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-123"
    assert "Video A" in payload["answer"]
    assert payload["model"] == "test-graph"
    assert payload["citations"][0]["label"] == "Video A Chunk 0"
    assert payload["citations"][0]["video_id"] == "A"

    # The user and assistant turns should both be persisted for follow-up memory.
    assert [m.role for m in memory.messages["session-123"]] == [ChatRole.USER, ChatRole.ASSISTANT]

    # Retrieval must be filtered by session id and respect top_k defaults.
    assert retriever.last_call == {
        "session_id": "session-123",
        "query": "Compare the hooks in the first 5 seconds.",
        "top_k": 8,
    }

    # LangGraph receives comparison metadata, memory, and retrieved evidence.
    assert graph.last_state["session_id"] == "session-123"
    assert graph.last_state["comparison"]["videos"]["A"]["engagement_rate"] == 7.2
    assert graph.last_state["retrieved_chunks"][0]["chunk_id"] == "chunk-A-0"


@pytest.mark.anyio
async def test_post_chat_returns_404_when_session_is_missing(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"session_id": "missing-session", "message": "What worked better?"},
        )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.anyio
async def test_post_chat_validates_blank_messages(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"session_id": "session-123", "message": "   "},
        )

    assert response.status_code == 422
