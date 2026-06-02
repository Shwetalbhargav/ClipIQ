"""End-to-end comparison orchestration and production adapters."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

from openai import AsyncOpenAI

from app.db.mongo import get_database
from app.modules.chat.schema import ChatMessage as ChatApiMessage
from app.modules.chat.schema import ChatRequest, ChatRole, RetrievedChunk as ChatRetrievedChunk, SourceCitation
from app.modules.chat.service import ChatService
from app.modules.engagement.schema import ENGAGEMENT_FORMULA, VideoEngagementInput
from app.modules.engagement.service import compare_videos
from app.modules.graph.nodes import GraphDependencies, create_build_context_node, create_compare_node
from app.modules.graph.workflow import run_graph
from app.modules.memory.schema import MemoryMessage, MemoryMessageCreate, MessageRole
from app.modules.memory.service import MongoMemoryRepository
from app.modules.transcript_processing.schema import TranscriptExtractionRequest, TranscriptExtractionResult
from app.modules.transcript_processing.service import TranscriptProcessingService
from app.modules.vector_store.schema import ChunkMetadata as VectorChunkMetadata
from app.modules.vector_store.schema import TranscriptChunkInput, VectorSearchRequest
from app.modules.vector_store.service import VectorStoreService
from app.modules.video_ingestion.schema import MetricValue, NormalizedVideoMetadata, SupportedPlatform
from app.modules.video_ingestion.service import VideoIngestionService

from .schema import ComparisonAnalyzeRequest, ComparisonAnalyzeResponse, ComparisonGetResponse, VideoSummary


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def jsonable_dataclass(value: Any) -> Any:
    if is_dataclass(value):
        return {key: jsonable_dataclass(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: jsonable_dataclass(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable_dataclass(item) for item in value]
    return value


def metric_value(metric: MetricValue | None) -> int | None:
    return None if metric is None else metric.value


class MongoComparisonRepository:
    """Mongo-backed persistence for comparisons, videos, metrics, and transcripts."""

    def __init__(self, db=None) -> None:
        self.db = db or get_database()

    async def create_comparison(self, *, comparison_id: str, youtube_url: str, instagram_url: str) -> None:
        now = utc_now()
        await self.db["comparisons"].insert_one(
            {
                "_id": comparison_id,
                "youtube_url": youtube_url,
                "instagram_url": instagram_url,
                "normalized_youtube_url": None,
                "normalized_instagram_url": None,
                "status": "processing",
                "error": None,
                "created_at": now,
                "updated_at": now,
            }
        )

    async def update_comparison(
        self,
        *,
        comparison_id: str,
        status: str,
        errors: list[dict[str, Any]],
        normalized_youtube_url: str | None,
        normalized_instagram_url: str | None,
    ) -> None:
        await self.db["comparisons"].update_one(
            {"_id": comparison_id},
            {
                "$set": {
                    "status": status,
                    "error": None if not errors else "; ".join(error.get("message", "") for error in errors)[:2000],
                    "normalized_youtube_url": normalized_youtube_url,
                    "normalized_instagram_url": normalized_instagram_url,
                    "errors": errors,
                    "updated_at": utc_now(),
                }
            },
            upsert=True,
        )

    async def save_video(self, *, comparison_id: str, label: str, metadata: NormalizedVideoMetadata) -> str:
        video_doc_id = f"{comparison_id}:{label}"
        now = utc_now()
        await self.db["videos"].update_one(
            {"_id": video_doc_id},
            {
                "$set": {
                    "_id": video_doc_id,
                    "comparison_id": comparison_id,
                    "video_label": label,
                    "platform": metadata.platform.value,
                    "source_url": str(metadata.source_url),
                    "canonical_url": metadata.canonical_url,
                    "platform_video_id": metadata.video_id,
                    "creator": metadata.creator,
                    "creator_followers": metric_value(metadata.follower_count),
                    "title": metadata.title,
                    "caption": metadata.caption,
                    "published_at": metadata.upload_date,
                    "duration_seconds": metadata.duration_seconds,
                    "thumbnail_url": metadata.thumbnail_url,
                    "hashtags": metadata.hashtags,
                    "raw_metadata": metadata.raw_metadata,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )
        return video_doc_id

    async def save_metric(
        self,
        *,
        comparison_id: str,
        video_doc_id: str,
        metadata: NormalizedVideoMetadata,
        engagement_rate: float | None,
    ) -> None:
        await self.db["video_metrics"].update_one(
            {"_id": f"{video_doc_id}:latest"},
            {
                "$set": {
                    "_id": f"{video_doc_id}:latest",
                    "comparison_id": comparison_id,
                    "video_id": video_doc_id,
                    "views": metric_value(metadata.views),
                    "likes": metric_value(metadata.likes),
                    "comments": metric_value(metadata.comments),
                    "shares": None,
                    "saves": None,
                    "engagement_rate": engagement_rate,
                    "engagement_formula": ENGAGEMENT_FORMULA,
                    "captured_at": utc_now(),
                }
            },
            upsert=True,
        )

    async def save_transcript_result(
        self,
        *,
        comparison_id: str,
        video_doc_id: str,
        label: str,
        platform: str,
        result: TranscriptExtractionResult,
        embedding_model: str,
    ) -> None:
        now = utc_now()
        if result.segments:
            await self.db["transcript_segments"].bulk_write(
                [
                    _replace_one(
                        {"_id": f"{video_doc_id}:segment:{segment.segment_index}"},
                        {
                            "_id": f"{video_doc_id}:segment:{segment.segment_index}",
                            "comparison_id": comparison_id,
                            "video_id": video_doc_id,
                            "segment_index": segment.segment_index,
                            "start_seconds": segment.start_seconds,
                            "end_seconds": segment.end_seconds,
                            "text": segment.text,
                            "source_type": segment.source_type.value,
                            "created_at": now,
                        },
                    )
                    for segment in result.segments
                ],
                ordered=False,
            )

        if result.chunks:
            await self.db["transcript_chunks"].bulk_write(
                [
                    _replace_one(
                        {"_id": f"{video_doc_id}:chunk:{chunk.chunk_index}"},
                        {
                            "_id": f"{video_doc_id}:chunk:{chunk.chunk_index}",
                            "comparison_id": comparison_id,
                            "video_id": video_doc_id,
                            "video_label": label,
                            "platform": platform,
                            "chunk_index": chunk.chunk_index,
                            "start_seconds": chunk.start_seconds,
                            "end_seconds": chunk.end_seconds,
                            "text": chunk.text,
                            "qdrant_point_id": None,
                            "embedding_model": embedding_model,
                            "metadata_version": 1,
                            "created_at": now,
                        },
                    )
                    for chunk in result.chunks
                ],
                ordered=False,
            )

    async def update_chunk_point_ids(self, *, updates: list[dict[str, str]]) -> None:
        if not updates:
            return
        await self.db["transcript_chunks"].bulk_write(
            [
                _update_one(
                    {"_id": item["chunk_doc_id"]},
                    {"$set": {"qdrant_point_id": item["point_id"]}},
                )
                for item in updates
            ],
            ordered=False,
        )

    async def get_comparison(self, comparison_id: str) -> dict[str, Any] | None:
        comparison = await self.db["comparisons"].find_one({"_id": comparison_id})
        if comparison is None:
            return None
        videos = await self.db["videos"].find({"comparison_id": comparison_id}).sort("video_label", 1).to_list(length=2)
        metrics = await self.db["video_metrics"].find({"comparison_id": comparison_id}).to_list(length=None)
        chunks = await self.db["transcript_chunks"].find({"comparison_id": comparison_id}).to_list(length=None)
        return {"comparison": comparison, "videos": videos, "metrics": metrics, "chunks": chunks}

    async def get_comparison_context(self, session_id: str) -> dict[str, Any] | None:
        return await self.get_comparison(session_id)

    async def get_video_metadata(self, *, comparison_id: str) -> dict[str, dict[str, Any]]:
        data = await self.get_comparison(comparison_id)
        if data is None:
            return {}
        metrics_by_video = {item["video_id"]: item for item in data["metrics"]}
        chunks_by_video = {
            label: [chunk for chunk in data["chunks"] if chunk.get("video_label") == label]
            for label in ("A", "B")
        }
        output: dict[str, dict[str, Any]] = {}
        for video in data["videos"]:
            label = video["video_label"]
            metric = metrics_by_video.get(video["_id"], {})
            chunks = chunks_by_video.get(label, [])
            output[label] = {
                "video_id": label,
                "platform": video.get("platform"),
                "source_url": video.get("source_url"),
                "creator": video.get("creator"),
                "title": video.get("title"),
                "published_at": video.get("published_at"),
                "duration_seconds": video.get("duration_seconds"),
                "views": metric.get("views"),
                "likes": metric.get("likes"),
                "comments": metric.get("comments"),
                "follower_count": video.get("creator_followers"),
                "hashtags": video.get("hashtags") or [],
                "engagement_rate": metric.get("engagement_rate"),
                "engagement_formula": metric.get("engagement_formula"),
                "transcript_status": "ready" if chunks else "unavailable",
            }
        return output


def _replace_one(filter_doc: dict[str, Any], replacement: dict[str, Any]):
    from pymongo import ReplaceOne

    return ReplaceOne(filter_doc, replacement, upsert=True)


def _update_one(filter_doc: dict[str, Any], update_doc: dict[str, Any]):
    from pymongo import UpdateOne

    return UpdateOne(filter_doc, update_doc)


class ProductionMemoryStore:
    """Adapter satisfying both ChatService and LangGraph memory protocols."""

    def __init__(self, repository: MongoMemoryRepository) -> None:
        self.repository = repository

    async def get_messages(self, session_id: str, *, limit: int = 6) -> list[ChatApiMessage]:
        messages = await self.repository.list_by_comparison(session_id, limit=limit)
        return [ChatApiMessage(role=ChatRole(message.role.value), content=message.content, created_at=message.created_at) for message in messages]

    async def append_message(self, *args, **kwargs) -> None:
        if args and len(args) == 2 and isinstance(args[1], ChatApiMessage):
            session_id, message = args
            role = MessageRole(message.role.value)
            content = message.content
        else:
            session_id = kwargs["comparison_id"]
            role = MessageRole(kwargs["role"])
            content = kwargs["content"]
        await self.repository.append(
            MemoryMessage.new(
                MemoryMessageCreate(
                    comparison_id=session_id,
                    role=role,
                    content=content,
                    metadata={},
                )
            )
        )

    async def get_recent_messages(self, *, comparison_id: str, limit: int = 6) -> list[dict[str, str]]:
        return [
            {"role": message.role.value, "content": message.content}
            for message in await self.repository.list_by_comparison(comparison_id, limit=limit)
        ]


class ProductionRetriever:
    """Qdrant-backed retriever for chat and LangGraph protocols."""

    def __init__(self, vector_service: VectorStoreService) -> None:
        self.vector_service = vector_service

    async def retrieve(self, **kwargs):
        comparison_id = kwargs.get("comparison_id") or kwargs.get("session_id")
        query = kwargs["query"]
        video_id = kwargs.get("video_id")
        top_k = kwargs.get("top_k", 8)
        results = await self.vector_service.search(
            VectorSearchRequest(
                query=query,
                comparison_id=comparison_id,
                video_id=video_id,
                top_k=top_k,
            )
        )
        if "session_id" in kwargs:
            return [
                ChatRetrievedChunk(
                    chunk_id=result.metadata.chunk_id,
                    video_id=result.metadata.video_id,
                    chunk_index=result.metadata.chunk_index,
                    text=result.text,
                    platform=result.metadata.platform,
                    source_url=result.metadata.source_url,
                    creator=result.metadata.creator,
                    start_seconds=getattr(result.metadata, "start_seconds", result.metadata.start_time),
                    end_seconds=getattr(result.metadata, "end_seconds", result.metadata.end_time),
                    score=result.score,
                )
                for result in results
            ]
        return [
            {
                "chunk_id": result.metadata.chunk_id,
                "comparison_id": result.metadata.comparison_id,
                "video_id": result.metadata.video_id,
                "platform": result.metadata.platform,
                "source_url": result.metadata.source_url,
                "creator": result.metadata.creator,
                "chunk_index": result.metadata.chunk_index,
                "start_seconds": getattr(result.metadata, "start_seconds", result.metadata.start_time),
                "end_seconds": getattr(result.metadata, "end_seconds", result.metadata.end_time),
                "text": result.text,
                "score": result.score,
            }
            for result in results
        ]


class OpenAIResponseGenerator:
    """Grounded response generator used by the LangGraph response node."""

    def __init__(self, *, api_key: str | None, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, *, question: str, context: str, memory: list[dict[str, str]]) -> str:
        memory_text = "\n".join(f"{item['role']}: {item['content']}" for item in memory[-6:])
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ClipIQ, a source-grounded social video analyst. "
                        "Use only the provided metadata and transcript chunks. "
                        "Cite transcript claims with labels like [Video A Chunk 0]. "
                        "Say when evidence is missing."
                    ),
                },
                {"role": "user", "content": f"MEMORY\n{memory_text}\n\nCONTEXT\n{context}\n\nQUESTION\n{question}"},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or "I could not generate an answer from the available evidence."


class ProductionGraphRunner:
    """Adapter around the compiled LangGraph workflow."""

    def __init__(self, deps: GraphDependencies) -> None:
        self.deps = deps

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        comparison_id = state.get("comparison_id") or state.get("session_id")
        result = await run_graph(self.deps, comparison_id=comparison_id, question=state["question"])
        return dict(result)


class ChatServiceStreamer:
    """Streaming adapter that emits true model token deltas for chat."""

    def __init__(
        self,
        chat_service: ChatService,
        *,
        graph_deps: GraphDependencies | None = None,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        self.chat_service = chat_service
        self.graph_deps = graph_deps
        self.openai = AsyncOpenAI(api_key=api_key) if graph_deps is not None else None
        self.model = model

    async def stream_chat(self, *, comparison_id: str, message: str, response_id: str, user_id: str | None = None):
        if self.graph_deps is None or self.openai is None:
            # Test/development fallback only. Production container supplies graph_deps
            # and OpenAI credentials so the frontend receives true model deltas.
            async for item in self._fallback_stream(comparison_id=comparison_id, message=message):
                yield item
            return

        memory = await self.graph_deps.memory_repo.get_recent_messages(comparison_id=comparison_id, limit=6)
        retrieved_a = await self.graph_deps.retriever.retrieve(
            comparison_id=comparison_id,
            video_id="A",
            query=message,
            top_k=self.graph_deps.top_k_per_video,
        )
        retrieved_b = await self.graph_deps.retriever.retrieve(
            comparison_id=comparison_id,
            video_id="B",
            query=message,
            top_k=self.graph_deps.top_k_per_video,
        )
        metadata = await self.graph_deps.metadata_repo.get_video_metadata(comparison_id=comparison_id)
        state: dict[str, Any] = {
            "comparison_id": comparison_id,
            "question": message,
            "memory": memory,
            "retrieved_a": retrieved_a,
            "retrieved_b": retrieved_b,
            "metadata": metadata,
        }
        state.update(await create_compare_node(self.graph_deps)(state))
        state.update(await create_build_context_node(self.graph_deps)(state))

        await self.graph_deps.memory_repo.append_message(
            comparison_id=comparison_id,
            role="user",
            content=message,
        )

        memory_text = "\n".join(f"{item['role']}: {item['content']}" for item in memory[-6:])
        stream = await self.openai.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are ClipIQ, a source-grounded social video analyst. "
                        "Use only the provided metadata and transcript chunks. "
                        "Cite transcript claims with labels like [Video A Chunk 0]. "
                        "Say when evidence is missing."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"MEMORY\n{memory_text}\n\n"
                        f"CONTEXT\n{state.get('context', '')}\n\n"
                        f"QUESTION\n{message}"
                    ),
                },
            ],
            temperature=0.2,
            stream=True,
        )

        answer_parts: list[str] = []
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue
            answer_parts.append(delta)
            yield delta

        answer = "".join(answer_parts).strip()
        await self.graph_deps.memory_repo.append_message(
            comparison_id=comparison_id,
            role="assistant",
            content=answer or "I could not generate an answer from the available evidence.",
        )

        for citation in state.get("citations", []):
            yield {"type": "citation", "data": citation}

    async def _fallback_stream(self, *, comparison_id: str, message: str):
        response = await self.chat_service.chat(ChatRequest(session_id=comparison_id, message=message))
        for token in response.answer.split(" "):
            yield token + " "
            await asyncio.sleep(0)
        for citation in response.citations:
            yield {"type": "citation", "data": citation.model_dump(mode="json")}


class ComparisonAnalysisService:
    """Coordinates metadata extraction, transcripts, Mongo persistence, and Qdrant indexing."""

    def __init__(
        self,
        *,
        repository: MongoComparisonRepository,
        ingestion_service: VideoIngestionService,
        transcript_service: TranscriptProcessingService,
        vector_service: VectorStoreService,
    ) -> None:
        self.repository = repository
        self.ingestion_service = ingestion_service
        self.transcript_service = transcript_service
        self.vector_service = vector_service

    async def analyze(self, request: ComparisonAnalyzeRequest) -> ComparisonAnalyzeResponse:
        comparison_id = str(uuid.uuid4())
        youtube_url = str(request.youtube_url)
        instagram_url = str(request.instagram_url)
        await self.repository.create_comparison(
            comparison_id=comparison_id,
            youtube_url=youtube_url,
            instagram_url=instagram_url,
        )

        errors: list[dict[str, Any]] = []
        ingestion = await self.ingestion_service.analyze_videos([youtube_url, instagram_url])
        errors.extend(error.model_dump(mode="json") for error in ingestion.errors)

        video_items = {item.label: item.metadata for item in ingestion.videos}
        video_doc_ids: dict[str, str] = {}
        transcript_results: dict[str, TranscriptExtractionResult] = {}
        indexed_counts = {"A": 0, "B": 0}

        for label in ("A", "B"):
            metadata = video_items.get(label)
            if metadata is None:
                continue
            video_doc_id = await self.repository.save_video(comparison_id=comparison_id, label=label, metadata=metadata)
            video_doc_ids[label] = video_doc_id

            engagement_rate = metadata.engagement_rate
            await self.repository.save_metric(
                comparison_id=comparison_id,
                video_doc_id=video_doc_id,
                metadata=metadata,
                engagement_rate=engagement_rate,
            )

            result = await asyncio.to_thread(
                self.transcript_service.process,
                TranscriptExtractionRequest(
                    video_id=label,
                    source_url=str(metadata.source_url),
                    platform=metadata.platform.value,
                    platform_video_id=metadata.video_id,
                    metadata={
                        "comparison_id": comparison_id,
                        "creator": metadata.creator,
                        "title": metadata.title,
                    },
                ),
            )
            transcript_results[label] = result
            if result.error:
                errors.append({"video_id": label, "code": "TRANSCRIPT_UNAVAILABLE", "message": result.error, "retryable": False})

            await self.repository.save_transcript_result(
                comparison_id=comparison_id,
                video_doc_id=video_doc_id,
                label=label,
                platform=metadata.platform.value,
                result=result,
                embedding_model=self.vector_service.settings.openai_embedding_model,
            )
            indexed_counts[label] = await self._index_chunks(
                comparison_id=comparison_id,
                label=label,
                video_doc_id=video_doc_id,
                metadata=metadata,
                result=result,
            )

        engagement = self._engagement_payload(video_items)
        status = self._status(video_items=video_items, transcript_results=transcript_results, errors=errors)
        await self.repository.update_comparison(
            comparison_id=comparison_id,
            status=status,
            errors=errors,
            normalized_youtube_url=video_items.get("A").canonical_url if video_items.get("A") else None,
            normalized_instagram_url=video_items.get("B").canonical_url if video_items.get("B") else None,
        )
        data = await self.repository.get_comparison(comparison_id)
        return self._response_from_data(
            data=data,
            comparison_id=comparison_id,
            status=status,
            errors=errors,
            transcript_results=transcript_results,
            indexed_counts=indexed_counts,
            video_items=video_items,
            engagement=engagement,
        )

    async def get(self, comparison_id: str) -> ComparisonGetResponse | None:
        data = await self.repository.get_comparison(comparison_id)
        if data is None:
            return None
        comparison = data["comparison"]
        video_items = self._video_items_from_data(data)
        indexed_counts = {
            label: sum(1 for chunk in data["chunks"] if chunk.get("video_label") == label and chunk.get("qdrant_point_id"))
            for label in ("A", "B")
        }
        response = self._response_from_data(
            data=data,
            comparison_id=comparison_id,
            status=comparison.get("status", "failed"),
            errors=comparison.get("errors", []),
            transcript_results={},
            indexed_counts=indexed_counts,
            video_items=video_items,
            engagement=self._stored_engagement_payload(data),
        )
        return ComparisonGetResponse(**response.model_dump(mode="json"))

    async def _index_chunks(
        self,
        *,
        comparison_id: str,
        label: str,
        video_doc_id: str,
        metadata: NormalizedVideoMetadata,
        result: TranscriptExtractionResult,
    ) -> int:
        inputs = [
            TranscriptChunkInput(
                text=chunk.text,
                metadata=VectorChunkMetadata(
                    comparison_id=comparison_id,
                    video_id=label,
                    chunk_id=f"{video_doc_id}:chunk:{chunk.chunk_index}",
                    chunk_index=chunk.chunk_index,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                    platform=metadata.platform.value,
                    source_url=str(metadata.source_url),
                    creator=metadata.creator,
                    title=metadata.title,
                ),
            )
            for chunk in result.chunks
            if chunk.text
        ]
        if not inputs:
            return 0
        indexed = await self.vector_service.index_chunks(inputs)
        await self.repository.update_chunk_point_ids(
            updates=[
                {"chunk_doc_id": item.chunk_id, "point_id": item.point_id}
                for item in indexed
            ]
        )
        return len(indexed)

    def _engagement_payload(self, video_items: dict[str, NormalizedVideoMetadata]) -> dict[str, Any]:
        if "A" not in video_items or "B" not in video_items:
            return {}
        comparison = compare_videos(
            VideoEngagementInput(
                video_id="A",
                label="A",
                platform=video_items["A"].platform.value,
                views=metric_value(video_items["A"].views),
                likes=metric_value(video_items["A"].likes),
                comments=metric_value(video_items["A"].comments),
                creator=video_items["A"].creator,
                title=video_items["A"].title,
                follower_count=metric_value(video_items["A"].follower_count),
            ),
            VideoEngagementInput(
                video_id="B",
                label="B",
                platform=video_items["B"].platform.value,
                views=metric_value(video_items["B"].views),
                likes=metric_value(video_items["B"].likes),
                comments=metric_value(video_items["B"].comments),
                creator=video_items["B"].creator,
                title=video_items["B"].title,
                follower_count=metric_value(video_items["B"].follower_count),
            ),
        )
        return jsonable_dataclass(comparison.as_dict())

    @staticmethod
    def _status(
        *,
        video_items: dict[str, NormalizedVideoMetadata],
        transcript_results: dict[str, TranscriptExtractionResult],
        errors: list[dict[str, Any]],
    ) -> str:
        if not video_items:
            return "failed"
        if set(video_items) == {"A", "B"} and all(result.chunks for result in transcript_results.values()) and not errors:
            return "ready"
        return "partial"

    def _response_from_data(
        self,
        *,
        data: dict[str, Any] | None,
        comparison_id: str,
        status: str,
        errors: list[dict[str, Any]],
        transcript_results: dict[str, TranscriptExtractionResult],
        indexed_counts: dict[str, int],
        video_items: dict[str, NormalizedVideoMetadata],
        engagement: dict[str, Any],
    ) -> ComparisonAnalyzeResponse:
        now = utc_now()
        created_at = data["comparison"].get("created_at", now) if data else now
        updated_at = data["comparison"].get("updated_at", now) if data else now
        return ComparisonAnalyzeResponse(
            comparison_id=comparison_id,
            status=status,
            video_a=self._summary("A", video_items.get("A"), transcript_results.get("A"), indexed_counts.get("A", 0))
            or self._stored_summary("A", data, indexed_counts.get("A", 0)),
            video_b=self._summary("B", video_items.get("B"), transcript_results.get("B"), indexed_counts.get("B", 0))
            or self._stored_summary("B", data, indexed_counts.get("B", 0)),
            transcript_status={
                label: result.status.value
                for label, result in transcript_results.items()
            } or self._stored_transcript_status(data),
            indexing_status={
                label: "indexed" if count else "not_indexed"
                for label, count in indexed_counts.items()
            },
            engagement=engagement,
            errors=errors,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def _summary(
        label: str,
        metadata: NormalizedVideoMetadata | None,
        transcript: TranscriptExtractionResult | None,
        indexed_count: int,
    ) -> VideoSummary | None:
        if metadata is None:
            return None
        return VideoSummary(
            label=label,
            video_id=metadata.video_id,
            platform=metadata.platform.value,
            source_url=str(metadata.source_url),
            canonical_url=metadata.canonical_url,
            creator=metadata.creator,
            follower_count=metric_value(metadata.follower_count),
            title=metadata.title,
            caption=metadata.caption,
            views=metric_value(metadata.views),
            likes=metric_value(metadata.likes),
            comments=metric_value(metadata.comments),
            engagement_rate=metadata.engagement_rate,
            hashtags=metadata.hashtags,
            upload_date=metadata.upload_date,
            duration_seconds=metadata.duration_seconds,
            thumbnail_url=metadata.thumbnail_url,
            transcript_status=transcript.status.value if transcript else "unavailable",
            chunk_count=len(transcript.chunks) if transcript else 0,
            indexed_chunk_count=indexed_count,
        )

    @staticmethod
    def _video_items_from_data(data: dict[str, Any]) -> dict[str, NormalizedVideoMetadata]:
        # GET can return summaries from stored docs through `_response_from_data`
        # when full Pydantic metadata is unavailable. This method is intentionally
        # left minimal because the POST response is the primary demo contract.
        return {}

    @staticmethod
    def _stored_transcript_status(data: dict[str, Any] | None) -> dict[str, str]:
        if data is None:
            return {}
        return {
            label: "ready" if any(chunk.get("video_label") == label for chunk in data.get("chunks", [])) else "unavailable"
            for label in ("A", "B")
        }

    @staticmethod
    def _stored_engagement_payload(data: dict[str, Any]) -> dict[str, Any]:
        videos_by_label = {video.get("video_label"): video for video in data.get("videos", [])}
        metrics_by_video = {metric.get("video_id"): metric for metric in data.get("metrics", [])}
        if "A" not in videos_by_label or "B" not in videos_by_label:
            return {}

        def input_for(label: str) -> VideoEngagementInput:
            video = videos_by_label[label]
            metric = metrics_by_video.get(video.get("_id"), {})
            return VideoEngagementInput(
                video_id=label,
                label=label,  # type: ignore[arg-type]
                platform=video.get("platform") or "unknown",
                views=metric.get("views"),
                likes=metric.get("likes"),
                comments=metric.get("comments"),
                creator=video.get("creator"),
                title=video.get("title"),
                follower_count=video.get("creator_followers"),
            )

        comparison = compare_videos(input_for("A"), input_for("B"))
        return jsonable_dataclass(comparison.as_dict())

    @staticmethod
    def _stored_summary(label: str, data: dict[str, Any] | None, indexed_count: int) -> VideoSummary | None:
        if data is None:
            return None
        video = next((item for item in data.get("videos", []) if item.get("video_label") == label), None)
        if video is None:
            return None
        metric = next((item for item in data.get("metrics", []) if item.get("video_id") == video.get("_id")), {})
        chunk_count = sum(1 for item in data.get("chunks", []) if item.get("video_label") == label)
        return VideoSummary(
            label=label,
            video_id=video.get("platform_video_id") or label,
            platform=video.get("platform"),
            source_url=video.get("source_url"),
            canonical_url=video.get("canonical_url"),
            creator=video.get("creator"),
            follower_count=video.get("creator_followers"),
            title=video.get("title"),
            caption=video.get("caption"),
            views=metric.get("views"),
            likes=metric.get("likes"),
            comments=metric.get("comments"),
            engagement_rate=metric.get("engagement_rate"),
            hashtags=video.get("hashtags") or [],
            upload_date=video.get("published_at"),
            duration_seconds=video.get("duration_seconds"),
            thumbnail_url=video.get("thumbnail_url"),
            transcript_status="ready" if chunk_count else "unavailable",
            chunk_count=chunk_count,
            indexed_chunk_count=indexed_count,
        )
