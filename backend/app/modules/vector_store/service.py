"""High-level vector store service for ClipIQ transcript retrieval.

Responsibilities:
- generate embeddings for transcript chunks and search queries
- create/maintain the Qdrant collection through the adapter
- upsert vectors with deterministic point IDs for idempotent indexing
- search vectors with mandatory comparison-scoped filtering

The service is intentionally thin around two external systems. It should be used
by ingestion/indexing workers and by LangGraph retrieval nodes, while MongoDB or
PostgreSQL remains the durable source of truth for canonical transcript records.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
import uuid
from collections.abc import Sequence
from typing import Any

from openai import AsyncOpenAI

from .qdrant import QdrantTranscriptStore, QdrantVectorStoreError
from .schema import IndexedVector, TranscriptChunkInput, VectorSearchRequest, VectorSearchResult, VectorStoreSettings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(RuntimeError):
    """Raised when embedding generation fails."""


class VectorStoreService:
    """Application-facing service for transcript embeddings and retrieval."""

    _POINT_NAMESPACE = uuid.UUID("1c66f0b9-2e71-4d08-9ddc-fcde32d0b8d5")
    _TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_']+")

    def __init__(
        self,
        settings: VectorStoreSettings,
        *,
        qdrant_store: QdrantTranscriptStore | None = None,
        openai_client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings
        self.qdrant = qdrant_store or QdrantTranscriptStore(settings)
        self.openai = openai_client
        if self.openai is None and settings.embedding_provider == "openai":
            self.openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self._sentence_transformer: Any | None = None

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
            embedding_model=self.embedding_model_name,
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
        """Generate embeddings in bounded batches.

        OpenAI accepts multiple inputs per request. Batching reduces HTTP overhead,
        while the configurable batch size prevents huge transcript jobs from
        creating overly large requests.
        """

        if not texts:
            return []

        normalized = [" ".join(text.split()) for text in texts]
        if any(not text for text in normalized):
            raise ValueError("All embedding inputs must contain non-whitespace text")

        if self.settings.embedding_provider == "local_hash":
            return [self._local_hash_embedding(text) for text in normalized]
        if self.settings.embedding_provider == "sentence_transformers":
            return await asyncio.to_thread(self._sentence_transformer_embeddings, normalized)

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
                if self.openai is None:
                    raise EmbeddingServiceError("OpenAI embeddings client is not configured")
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

    @property
    def embedding_model_name(self) -> str:
        """Return the model label persisted with chunk payloads."""

        if self.settings.embedding_provider == "openai":
            return self.settings.openai_embedding_model
        if self.settings.embedding_provider == "sentence_transformers":
            return self.settings.embedding_model
        return "local-hash-embedding"

    def _sentence_transformer_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate local open-source embeddings with sentence-transformers."""

        model = self._get_sentence_transformer()
        values = model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [self._fit_vector_size([float(value) for value in row]) for row in values]

    def _get_sentence_transformer(self) -> Any:
        """Lazy-load the local embedding model after app startup."""

        if self._sentence_transformer is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise EmbeddingServiceError(
                    "sentence-transformers is required for EMBEDDING_PROVIDER=sentence_transformers. "
                    "Install it with: python -m pip install sentence-transformers"
                ) from exc
            self._sentence_transformer = SentenceTransformer(self.settings.embedding_model)
        return self._sentence_transformer

    def _fit_vector_size(self, vector: list[float]) -> list[float]:
        """Pad or truncate local model vectors to match the Qdrant collection."""

        target_size = self.settings.qdrant_vector_size
        if len(vector) == target_size:
            return vector
        if len(vector) > target_size:
            return vector[:target_size]
        return vector + [0.0] * (target_size - len(vector))

    def _local_hash_embedding(self, text: str) -> list[float]:
        """Create a deterministic local vector for quota-free demo retrieval."""

        vector = [0.0] * self.settings.qdrant_vector_size
        tokens = self._TOKEN_PATTERN.findall(text.lower()) or [text.lower()]

        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], byteorder="big") % self.settings.qdrant_vector_size
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

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
