from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.core.config import get_settings


_qdrant_client: AsyncQdrantClient | None = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _qdrant_client

    if _qdrant_client is None:
        settings = get_settings()

        api_key = settings.qdrant_api_key or None

        _qdrant_client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=api_key,
            timeout=10,
        )

    return _qdrant_client


async def ping_qdrant() -> bool:
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception:
        return False


async def init_qdrant_collection() -> None:
    settings = get_settings()
    client = get_qdrant_client()

    collections = await client.get_collections()
    existing_names = {collection.name for collection in collections.collections}

    if settings.qdrant_collection not in existing_names:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=settings.embedding_dimension,
                distance=models.Distance.COSINE,
            ),
        )

    await create_payload_indexes()


async def create_payload_indexes() -> None:
    settings = get_settings()
    client = get_qdrant_client()
    collection = settings.qdrant_collection

    payload_indexes = {
        "comparison_id": models.PayloadSchemaType.KEYWORD,
        "video_id": models.PayloadSchemaType.KEYWORD,
        "video_label": models.PayloadSchemaType.KEYWORD,
        "platform": models.PayloadSchemaType.KEYWORD,
        "chunk_index": models.PayloadSchemaType.INTEGER,
        "creator": models.PayloadSchemaType.KEYWORD,
    }

    for field_name, field_schema in payload_indexes.items():
        try:
            await client.create_payload_index(
                collection_name=collection,
                field_name=field_name,
                field_schema=field_schema,
            )
        except Exception:
            # Qdrant throws if index already exists depending on version.
            # Safe to ignore for idempotent local setup.
            pass


async def close_qdrant() -> None:
    global _qdrant_client

    if _qdrant_client is not None:
        await _qdrant_client.close()

    _qdrant_client = None