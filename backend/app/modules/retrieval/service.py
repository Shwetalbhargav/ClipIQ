"""Retrieval service for ClipIQ.

This module owns the retrieval flow:
1. Embed the user's question.
2. Build a metadata filter so retrieval stays inside the active comparison.
3. Run top-k vector similarity search.
4. Normalize vector-store payloads into app schemas.
5. Generate stable citations for the chat/streaming layer.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from typing import Any, Protocol

from .citation import generate_citations
from .schema import ChunkMetadata, RetrievalFilter, RetrievalRequest, RetrievalResult, RetrievedChunk

logger = logging.getLogger(__name__)

EmbeddingFn = Callable[[str], Awaitable[list[float]]]


class VectorSearchClient(Protocol):
    """Small protocol implemented by Qdrant/Chroma adapters.

    Keep this interface narrow so the retrieval module is easy to test and the
    vector database can be swapped without rewriting LangGraph nodes.
    """

    async def search(
        self,
        *,
        vector: Sequence[float],
        top_k: int,
        filters: dict[str, Any],
        score_threshold: float | None = None,
    ) -> Sequence[Any]:
        """Return vector-store points with id, score, and payload attributes."""


class RetrievalService:
    """Coordinates similarity search, metadata filtering, and citations."""

    def __init__(self, *, vector_client: VectorSearchClient, embed_query: EmbeddingFn) -> None:
        self._vector_client = vector_client
        self._embed_query = embed_query

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        """Retrieve top-k chunks for a query and generate source citations."""

        logger.info(
            "retrieval.start",
            extra={
                "comparison_id": request.filters.comparison_id,
                "top_k": request.top_k,
                "has_video_filter": bool(request.filters.video_id or request.filters.video_label),
            },
        )

        # Step 1: embed the question with the same model used for transcript chunks.
        query_vector = await self._embed_query(request.query)

        # Step 2: enforce scoped retrieval. This prevents cross-comparison leakage.
        vector_filters = build_metadata_filter(request.filters)

        # Step 3: ask the vector DB for the most similar chunks.
        raw_points = await self._vector_client.search(
            vector=query_vector,
            top_k=request.top_k,
            filters=vector_filters,
            score_threshold=request.score_threshold,
        )

        # Step 4: normalize DB-specific point objects/dicts into internal schemas.
        chunks = [point_to_chunk(point) for point in raw_points]

        # Step 5: citations are derived directly from retrieved chunks.
        citations = generate_citations(chunks)

        logger.info(
            "retrieval.done",
            extra={
                "comparison_id": request.filters.comparison_id,
                "query_len": len(request.query),
                "returned": len(chunks),
            },
        )

        return RetrievalResult(query=request.query, chunks=chunks, citations=citations)


def build_metadata_filter(filters: RetrievalFilter) -> dict[str, Any]:
    """Build vector-store metadata filters from request constraints.

    The shape is intentionally simple: adapters can translate this dictionary
    into Qdrant Filter objects, Chroma `where` clauses, or pgvector SQL WHEREs.
    """

    metadata_filter: dict[str, Any] = {"comparison_id": filters.comparison_id}

    if filters.video_id:
        metadata_filter["video_id"] = filters.video_id
    if filters.video_label:
        metadata_filter["video_label"] = filters.video_label
    if filters.platform:
        metadata_filter["platform"] = filters.platform.lower()
    if filters.creator:
        metadata_filter["creator"] = filters.creator

    return metadata_filter


def point_to_chunk(point: Any) -> RetrievedChunk:
    """Convert a vector-store point into a RetrievedChunk.

    Supported point forms:
    - dicts returned by in-memory tests or custom adapters
    - objects with `.id`, `.score`, and `.payload` attributes, like Qdrant results
    """

    if isinstance(point, dict):
        point_id = str(point.get("id") or point.get("point_id") or point.get("chunk_id"))
        score = float(point.get("score", 0.0))
        payload = dict(point.get("payload") or point)
    else:
        point_id = str(getattr(point, "id", ""))
        score = float(getattr(point, "score", 0.0))
        payload = dict(getattr(point, "payload", {}) or {})

    text = str(payload.get("text") or payload.get("page_content") or "").strip()
    if not text:
        logger.warning("retrieval.empty_chunk_text", extra={"point_id": point_id})

    metadata = ChunkMetadata(
        comparison_id=str(payload["comparison_id"]),
        video_id=str(payload["video_id"]),
        video_label=payload.get("video_label"),
        platform=str(payload["platform"]).lower(),
        source_url=payload.get("source_url"),
        creator=payload.get("creator"),
        chunk_id=str(payload.get("chunk_id") or point_id),
        chunk_index=int(payload.get("chunk_index", 0)),
        start_seconds=_optional_float(payload.get("start_seconds", payload.get("start_time"))),
        end_seconds=_optional_float(payload.get("end_seconds", payload.get("end_time"))),
        title=payload.get("title"),
        extra={
            key: value
            for key, value in payload.items()
            if key
            not in {
                "comparison_id",
                "video_id",
                "video_label",
                "platform",
                "source_url",
                "creator",
                "chunk_id",
                "chunk_index",
                "start_seconds",
                "start_time",
                "end_seconds",
                "end_time",
                "title",
                "text",
                "page_content",
            }
        },
    )

    return RetrievedChunk(id=point_id, text=text, score=score, metadata=metadata)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
