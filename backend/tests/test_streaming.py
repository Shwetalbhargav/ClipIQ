"""Tests for Module 9 streaming SSE behavior."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.streaming.router import router
from app.modules.streaming.service import StreamingService, encode_sse, normalize_stream_item, StreamEvent

class FakeChatStreamer:
    """Tiny async fake that behaves like a LangGraph token stream."""

    async def stream_chat(
        self,
        *,
        comparison_id: str,
        message: str,
        response_id: str,
        user_id: str | None = None,
    ) -> AsyncIterator[str | dict]:
        yield "Video A "
        yield {"type": "delta", "text": "wins on hook clarity."}
        yield {
            "type": "citation",
            "citation_id": "A-0",
            "video_id": "A",
            "chunk_id": "chunk-a-0",
            "chunk_index": 0,
            "start_seconds": 0,
            "end_seconds": 5,
            "label": "Video A · Chunk 0 · 0-5s",
        }


class ExplodingChatStreamer:
    async def stream_chat(self, **kwargs) -> AsyncIterator[str | dict]:
        yield "partial token"
        raise RuntimeError("provider exploded with secret-ish stack details")


def _build_client(streamer) -> TestClient:
    app = FastAPI()
    app.state.streaming_service = StreamingService(streamer, model_name="test-model")
    app.include_router(router)
    return TestClient(app)


def _parse_sse(body: str) -> list[tuple[str, dict]]:
    """Parse compact SSE frames emitted by the service into test-friendly tuples."""

    parsed: list[tuple[str, dict]] = []
    for frame in body.strip().split("\n\n"):
        event_name = None
        payload = None
        for line in frame.splitlines():
            if line.startswith("event: "):
                event_name = line.removeprefix("event: ")
            if line.startswith("data: "):
                payload = json.loads(line.removeprefix("data: "))
        assert event_name is not None
        assert payload is not None
        parsed.append((event_name, payload))
    return parsed


def test_encode_sse_uses_frontend_compatible_event_and_json_data() -> None:
    frame = encode_sse(StreamEvent(type="delta", data={"type": "delta", "text": "hello"}))

    assert frame == 'event: delta\ndata: {"type":"delta","text":"hello"}\n\n'


def test_normalize_plain_string_as_delta_token() -> None:
    event = normalize_stream_item("hello")

    assert event is not None
    assert event.type == "delta"
    assert event.data == {"type": "delta", "text": "hello"}


def test_streaming_endpoint_emits_metadata_delta_citation_and_done() -> None:
    client = _build_client(FakeChatStreamer())

    with client.stream(
        "POST",
        "/api/comparisons/cmp_123/chat/stream",
        json={"message": "Why did A outperform B?"},
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(body)
    event_names = [name for name, _ in events]

    assert event_names == ["metadata", "delta", "delta", "citation", "done"]
    assert events[0][1]["comparison_id"] == "cmp_123"
    assert events[1][1]["text"] == "Video A "
    assert events[3][1]["video_id"] == "A"
    assert events[-1][1]["usage"]["streamed_delta_count"] == 2
    assert events[-1][1]["usage"]["citation_count"] == 1


def test_streaming_endpoint_converts_upstream_failure_to_safe_error_event() -> None:
    client = _build_client(ExplodingChatStreamer())

    with client.stream(
        "POST",
        "/api/comparisons/cmp_123/chat/stream",
        json={"message": "Trigger failure"},
    ) as response:
        body = response.read().decode("utf-8")

    events = _parse_sse(body)

    assert response.status_code == 200
    assert events[-1][0] == "error"
    assert events[-1][1]["error"]["code"] == "stream_failed"
    assert "secret-ish" not in json.dumps(events[-1][1])


def test_streaming_endpoint_returns_error_event_for_invalid_message() -> None:
    client = _build_client(FakeChatStreamer())

    # Bypass Pydantic min_length by sending whitespace. The service should still
    # protect downstream graph calls and return an SSE error frame.
    response = client.post("/api/comparisons/cmp_123/chat/stream", json={"message": "   "})
    events = _parse_sse(response.text)

    assert response.status_code == 200
    assert events[0][0] == "error"
    assert events[0][1]["error"]["code"] == "bad_request"
