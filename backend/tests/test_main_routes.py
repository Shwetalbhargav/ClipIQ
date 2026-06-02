from fastapi.testclient import TestClient

import app.main as main


class FakeContainer:
    def __init__(self) -> None:
        self.comparison_repository = object()
        self.memory_store = object()
        self.retriever = object()
        self.graph_runner = object()
        self.chat_service = object()
        self.streaming_service = object()
        self.analysis_service = object()

    async def close(self) -> None:
        return None


async def fake_init_databases() -> None:
    return None


async def fake_close() -> None:
    return None


async def fake_build_app_container() -> FakeContainer:
    return FakeContainer()


def test_openapi_contains_production_routes() -> None:
    paths = set(main.app.openapi()["paths"])
    assert "/api/health" in paths
    assert "/api/comparisons" in paths
    assert "/api/chat" in paths
    assert "/api/comparisons/{comparison_id}/chat/stream" in paths


def test_startup_attaches_production_services(monkeypatch) -> None:
    monkeypatch.setattr(main, "init_databases", fake_init_databases)
    monkeypatch.setattr(main, "build_app_container", fake_build_app_container)
    monkeypatch.setattr(main, "close_qdrant", fake_close)
    monkeypatch.setattr(main, "close_mongo", fake_close)

    with TestClient(main.app) as client:
        assert hasattr(client.app.state, "comparison_repository")
        assert hasattr(client.app.state, "memory_store")
        assert hasattr(client.app.state, "retriever")
        assert hasattr(client.app.state, "graph_runner")
        assert hasattr(client.app.state, "chat_service")
        assert hasattr(client.app.state, "streaming_service")
        assert hasattr(client.app.state, "analysis_service")
