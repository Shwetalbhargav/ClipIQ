from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.chat.router import router
from app.modules.chat.schema import ChatResponse


class FakeChatService:
    def __init__(self) -> None:
        self.called = False

    async def chat(self, payload):
        self.called = True
        return ChatResponse(session_id=payload.session_id, answer="ok", citations=[], model="fake")


def test_chat_route_uses_app_state_chat_service() -> None:
    app = FastAPI()
    service = FakeChatService()
    app.state.chat_service = service
    app.include_router(router, prefix="/api")

    client = TestClient(app)
    response = client.post("/api/chat", json={"session_id": "cmp-1", "message": "What worked?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "ok"
    assert service.called is True


def test_chat_route_returns_503_without_service() -> None:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    client = TestClient(app)

    response = client.post("/api/chat", json={"session_id": "cmp-1", "message": "What worked?"})

    assert response.status_code == 503
