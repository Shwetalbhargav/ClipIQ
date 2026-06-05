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


class FakeSentenceTransformer:
    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False):
        return [[1.0, 0.0, 0.5] for _ in texts]


@pytest.mark.asyncio
async def test_sentence_transformer_embeddings_are_padded_to_qdrant_size() -> None:
    service = VectorStoreService(
        VectorStoreSettings(
            embedding_provider="sentence_transformers",
            embedding_model="BAAI/bge-small-en-v1.5",
            qdrant_vector_size=5,
        ),
        qdrant_store=FailingStartupQdrant(),
    )
    service._sentence_transformer = FakeSentenceTransformer()

    vectors = await service.embed_texts(["hello world"])

    assert vectors == [[1.0, 0.0, 0.5, 0.0, 0.0]]
    assert service.embedding_model_name == "BAAI/bge-small-en-v1.5"
