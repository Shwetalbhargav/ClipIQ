from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.streaming.router import router


class FakeStreamingService:
    def __init__(self) -> None:
        self.called = False

    async def stream_response(self, **kwargs) -> AsyncIterator[str]:
        self.called = True
        yield 'event: metadata\ndata: {"type":"metadata"}\n\n'
        yield 'event: done\ndata: {"type":"done"}\n\n'


def test_streaming_route_uses_app_state_streaming_service() -> None:
    app = FastAPI()
    service = FakeStreamingService()
    app.state.streaming_service = service
    app.include_router(router)

    client = TestClient(app)
    with client.stream("POST", "/api/comparisons/cmp-1/chat/stream", json={"message": "stream"}) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: metadata" in body
    assert service.called is True


def test_streaming_route_returns_503_without_service() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post("/api/comparisons/cmp-1/chat/stream", json={"message": "stream"})

    assert response.status_code == 503
