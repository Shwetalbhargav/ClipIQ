"""High-level vector store service for ClipIQ transcript retrieval.

Responsibilities:
- generate OpenAI embeddings for transcript chunks and search queries
- create/maintain the Qdrant collection through the adapter
- upsert vectors with deterministic point IDs for idempotent indexing
- search vectors with mandatory comparison-scoped filtering

The service is intentionally thin around two external systems. It should be used
by ingestion/indexing workers and by LangGraph retrieval nodes, while MongoDB or
PostgreSQL remains the durable source of truth for canonical transcript records.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Sequence

from openai import AsyncOpenAI

from .qdrant import QdrantTranscriptStore, QdrantVectorStoreError
from .schema import IndexedVector, TranscriptChunkInput, VectorSearchRequest, VectorSearchResult, VectorStoreSettings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Raised when embedding generation fails."""


class VectorStoreService:
    """Application-facing service for transcript embeddings and retrieval."""

    _POINT_NAMESPACE = uuid.UUID("1c66f0b9-2e71-4d08-9ddc-fcde32d0b8d5")

    def __init__(
        self,
        settings: VectorStoreSettings,
        *,
        qdrant_store: QdrantTranscriptStore | None = None,
        openai_client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings
        self.qdrant = qdrant_store or QdrantTranscriptStore(settings)
        self.openai = openai_client or AsyncOpenAI(api_key=settings.openai_api_key)

    async def startup(self) -> None:
        """Prepare Qdrant resources at application or worker startup."""

        try:
            await self.qdrant.ensure_collection()
        except QdrantVectorStoreError as exc:
            logger.warning("Qdrant startup check failed; API will start in degraded mode: %s", exc)

    async def index_chunks(self, chunks: Sequence[TranscriptChunkInput]) -> list[IndexedVector]:
        """Embed and upsert transcript chunks.

        The method is idempotent as long as the caller supplies stable
        comparison_id/video_id/chunk_id values. Existing Qdrant points are updated
        in place using deterministic UUIDv5 point IDs.
        """

        if not chunks:
            return []

        vectors = await self.embed_texts([chunk.text for chunk in chunks])
        point_ids = [self.make_point_id(chunk) for chunk in chunks]

        indexed = await self.qdrant.upsert_chunks(
            chunks=chunks,
            vectors=vectors,
            point_ids=point_ids,
            embedding_model=self.settings.openai_embedding_model,
        )

        logger.info(
            "Indexed %s transcript chunks into Qdrant collection=%s",
            len(indexed),
            self.settings.qdrant_collection,
        )
        return indexed

    async def search(self, request: VectorSearchRequest) -> list[VectorSearchResult]:
        """Embed a user query and retrieve matching transcript chunks."""

        query_vector = (await self.embed_texts([request.query]))[0]
        return await self.qdrant.search(
            query_vector=query_vector,
            comparison_id=request.comparison_id,
            video_id=request.video_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
        )

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate OpenAI embeddings in bounded batches.

        OpenAI accepts multiple inputs per request. Batching reduces HTTP overhead,
        while the configurable batch size prevents huge transcript jobs from
        creating overly large requests.
        """

        if not texts:
            return []

        normalized = [" ".join(text.split()) for text in texts]
        if any(not text for text in normalized):
            raise ValueError("All embedding inputs must contain non-whitespace text")

        vectors: list[list[float]] = []
        for start in range(0, len(normalized), self.settings.embedding_batch_size):
            batch = normalized[start : start + self.settings.embedding_batch_size]
            vectors.extend(await self._embed_batch(batch))

        return vectors

    async def _embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Call OpenAI embeddings API with retry for transient failures.

        This keeps the module dependency-light. In production, you may replace
        this with tenacity/backoff plus metrics around latency and token usage.
        """

        max_attempts = 3
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.openai.embeddings.create(
                    model=self.settings.openai_embedding_model,
                    input=list(texts),
                )
                # The API returns embeddings in the same order as input. Sorting by
                # index makes that contract explicit and protects against future
                # client-shape changes.
                ordered = sorted(response.data, key=lambda item: item.index)
                return [list(item.embedding) for item in ordered]
            except Exception as exc:  # pragma: no cover - exact OpenAI exceptions vary by SDK version
                last_error = exc
                if attempt == max_attempts:
                    break
                sleep_seconds = 0.5 * attempt
                logger.warning(
                    "OpenAI embedding attempt %s/%s failed; retrying in %.1fs: %s",
                    attempt,
                    max_attempts,
                    sleep_seconds,
                    exc,
                )
                await asyncio.sleep(sleep_seconds)

        raise EmbeddingServiceError(f"Failed to generate embeddings: {last_error}") from last_error

    def make_point_id(self, chunk: TranscriptChunkInput) -> str:
        """Build a deterministic Qdrant point ID for idempotent upserts."""

        key = ":".join(
            [
                chunk.metadata.comparison_id,
                chunk.metadata.video_id,
                chunk.metadata.chunk_id,
                str(chunk.metadata.chunk_index),
            ]
        )
        return str(uuid.uuid5(self._POINT_NAMESPACE, key))

    async def delete_comparison(self, comparison_id: str) -> None:
        """Delete all vector points for a comparison/session."""

        await self.qdrant.delete_comparison(comparison_id)

    async def close(self) -> None:
        """Release network resources held by the Qdrant client."""

        await self.qdrant.close()
