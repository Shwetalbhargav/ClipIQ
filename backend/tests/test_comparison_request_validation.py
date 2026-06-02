from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.comparisons.router import router


class DummyAnalysisService:
    async def analyze(self, payload):
        return {}


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.analysis_service = DummyAnalysisService()
    return TestClient(app)


def test_request_with_only_one_url_fails() -> None:
    client = build_client()
    response = client.post(
        "/api/comparisons",
        json={"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 422


def test_request_with_two_youtube_urls_fails() -> None:
    client = build_client()
    response = client.post(
        "/api/comparisons",
        json={
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "instagram_url": "https://www.youtube.com/watch?v=abc12345678",
        },
    )
    assert response.status_code == 422


def test_request_with_tiktok_fails() -> None:
    client = build_client()
    response = client.post(
        "/api/comparisons",
        json={
            "youtube_url": "https://www.tiktok.com/@creator/video/123",
            "instagram_url": "https://www.instagram.com/reel/CxYz123abcd/",
        },
    )
    assert response.status_code == 422
