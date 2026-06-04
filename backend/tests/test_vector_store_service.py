import pytest

from app.modules.vector_store.qdrant import QdrantVectorStoreError
from app.modules.vector_store.schema import VectorStoreSettings
from app.modules.vector_store.service import VectorStoreService


class FailingStartupQdrant:
    async def ensure_collection(self):
        raise QdrantVectorStoreError("All connection attempts failed")

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_startup_logs_qdrant_failure_without_crashing(caplog) -> None:
    service = VectorStoreService(
        VectorStoreSettings(openai_api_key="test-key"),
        qdrant_store=FailingStartupQdrant(),
    )

    await service.startup()

    assert "API will start in degraded mode" in caplog.text
