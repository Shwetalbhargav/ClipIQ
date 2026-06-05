"""Chat orchestration service for ClipIQ.

This module is framework-light and dependency-injected so it can be tested
without real OpenAI, Qdrant/Chroma, MongoDB, or LangGraph credentials. In the
application, wire concrete implementations for memory, retrieval, and graph.
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .schema import ChatMessage, ChatRequest, ChatResponse, ChatRole, RetrievedChunk, SourceCitation

logger = logging.getLogger(__name__)


class ChatModuleError(RuntimeError):
    """Base exception for expected chat-module failures."""


class SessionNotReadyError(ChatModuleError):
    """Raised when a chat request targets an unknown or unindexed session."""


class GraphExecutionError(ChatModuleError):
    """Raised when the LangGraph workflow cannot produce an answer."""


@runtime_checkable
class ChatMemoryStore(Protocol):
    """Persistence interface for session-scoped chat memory.

    A MongoDB-backed implementation should store messages in a collection keyed
    by comparison/session id. Tests can use a simple in-memory implementation.
    """

    async def get_messages(self, session_id: str, *, limit: int = 6) -> list[ChatMessage]:
        """Return recent chat turns in chronological order."""

    async def append_message(self, session_id: str, message: ChatMessage) -> None:
        """Persist one chat turn."""


@runtime_checkable
class Retriever(Protocol):
    """Vector retrieval interface.

    The concrete implementation should filter by session/comparison id before
    semantic search. That filtering is non-negotiable for source isolation.
    """

    async def retrieve(self, *, session_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        """Return session-filtered transcript chunks relevant to the query."""


@runtime_checkable
class ComparisonRepository(Protocol):
    """Repository interface for structured comparison/video metadata."""

    async def get_comparison_context(self, session_id: str) -> dict[str, Any] | None:
        """Return normalized metadata/metrics for the current comparison."""


@runtime_checkable
class LangGraphRunner(Protocol):
    """Minimal adapter around the real LangGraph compiled graph.

    The adapter may call `graph.ainvoke(state)`, stream internally and join the
    final answer, or use a test double. Keeping this as a protocol makes the
    FastAPI layer independent from LangGraph initialization details.
    """

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the chat graph and return at least an `answer` field."""


@dataclass(slots=True)
class ChatServiceConfig:
    """Runtime knobs for cost, memory, and model reporting."""

    model_name: str = "gpt-4o-mini"
    memory_turn_limit: int = 6
    default_top_k: int = 8


class ChatService:
    """Application service that owns chat request orchestration.

    Flow:
    1. Validate the session exists and load structured metadata.
    2. Load recent session memory.
    3. Persist the user's new message before generation for auditability.
    4. Retrieve session-filtered chunks.
    5. Invoke LangGraph with metadata, memory, user query, and chunks.
    6. Normalize citations and persist the assistant response.
    """

    def __init__(
        self,
        *,
        memory_store: ChatMemoryStore,
        retriever: Retriever,
        comparison_repository: ComparisonRepository,
        graph_runner: LangGraphRunner,
        config: ChatServiceConfig | None = None,
    ) -> None:
        self.memory_store = memory_store
        self.retriever = retriever
        self.comparison_repository = comparison_repository
        self.graph_runner = graph_runner
        self.config = config or ChatServiceConfig()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Answer one chat turn for a ready comparison session."""

        comparison_context = await self.comparison_repository.get_comparison_context(request.session_id)
        if comparison_context is None:
            raise SessionNotReadyError(
                "Session was not found or is not ready for chat. Run video analysis before asking questions."
            )

        # Load memory before appending the current user message so the graph gets
        # prior turns and the current query separately. This keeps prompt
        # construction cleaner and avoids duplicate user messages.
        memory = await self.memory_store.get_messages(
            request.session_id,
            limit=self.config.memory_turn_limit,
        )

        user_message = ChatMessage(role=ChatRole.USER, content=request.message)
        await self.memory_store.append_message(request.session_id, user_message)

        try:
            chunks = await self.retriever.retrieve(
                session_id=request.session_id,
                query=request.message,
                top_k=request.top_k or self.config.default_top_k,
            )
        except Exception as exc:
            logger.warning("Chat retrieval failed; using local comparison fallback", exc_info=True)
            fallback = self._local_fallback_response(
                request=request,
                comparison_context=comparison_context,
                reason=f"Semantic retrieval is unavailable: {exc}",
            )
            await self.memory_store.append_message(
                request.session_id,
                ChatMessage(role=ChatRole.ASSISTANT, content=fallback.answer),
            )
            return fallback

        graph_state = self._build_graph_state(
            request=request,
            memory=memory,
            comparison_context=comparison_context,
            chunks=chunks,
        )

        try:
            graph_result = await self.graph_runner.ainvoke(graph_state)
        except Exception as exc:  # pragma: no cover - defensive production logging branch
            logger.exception("LangGraph chat execution failed", extra={"session_id": request.session_id})
            fallback = self._local_fallback_response(
                request=request,
                comparison_context=comparison_context,
                chunks=chunks,
                reason=f"Model generation is unavailable: {exc}",
            )
            await self.memory_store.append_message(
                request.session_id,
                ChatMessage(role=ChatRole.ASSISTANT, content=fallback.answer),
            )
            return fallback

        answer = self._extract_answer(graph_result)
        citations = self._extract_citations(graph_result, chunks)
        usage = graph_result.get("usage", {}) if isinstance(graph_result, dict) else {}
        model = graph_result.get("model", self.config.model_name) if isinstance(graph_result, dict) else self.config.model_name

        await self.memory_store.append_message(
            request.session_id,
            ChatMessage(role=ChatRole.ASSISTANT, content=answer),
        )

        return ChatResponse(
            session_id=request.session_id,
            answer=answer,
            citations=citations,
            model=model,
            usage=usage,
        )

    def _local_fallback_response(
        self,
        *,
        request: ChatRequest,
        comparison_context: dict[str, Any],
        chunks: list[RetrievedChunk] | None = None,
        reason: str,
    ) -> ChatResponse:
        """Return a deterministic answer when vector search or LLM generation is unavailable."""

        videos = comparison_context.get("videos") or []
        metrics = comparison_context.get("metrics") or []
        stored_chunks = comparison_context.get("chunks") or []

        metrics_by_video = {item.get("video_id"): item for item in metrics if isinstance(item, dict)}
        lines = [
            "I can still help from the stored comparison data, but the full RAG path is unavailable right now.",
            reason,
            "",
            f"Question: {request.message}",
        ]

        for video in videos:
            if not isinstance(video, dict):
                continue
            label = video.get("video_label") or "?"
            metric = metrics_by_video.get(video.get("_id"), {})
            details = [
                f"Video {label} ({video.get('platform', 'unknown')})",
                f"title: {video.get('title') or 'unavailable'}",
                f"creator: {video.get('creator') or 'unavailable'}",
                f"views: {metric.get('views') if metric.get('views') is not None else 'unavailable'}",
                f"likes: {metric.get('likes') if metric.get('likes') is not None else 'unavailable'}",
                f"comments: {metric.get('comments') if metric.get('comments') is not None else 'unavailable'}",
                f"engagement rate: {metric.get('engagement_rate') if metric.get('engagement_rate') is not None else 'unavailable'}",
            ]
            lines.append("; ".join(details) + ".")

        if stored_chunks:
            lines.append("Transcript text is stored, but semantic ranking is unavailable, so I am citing the first available chunks.")
        else:
            lines.append("No transcript chunks are available for citation.")

        fallback_citations = [chunk.to_citation() for chunk in (chunks or [])[:4]]
        if not fallback_citations:
            for chunk in stored_chunks[:4]:
                if not isinstance(chunk, dict):
                    continue
                fallback_citations.append(
                    SourceCitation(
                        label=f"Video {chunk.get('video_label', '?')} Chunk {chunk.get('chunk_index', 0)}",
                        video_id=chunk.get("video_label") or "?",
                        chunk_id=chunk.get("_id"),
                        chunk_index=chunk.get("chunk_index"),
                        platform=chunk.get("platform"),
                        start_seconds=chunk.get("start_seconds"),
                        end_seconds=chunk.get("end_seconds"),
                        text=(chunk.get("text") or "")[:500],
                        metadata={"fallback": True},
                    )
                )

        return ChatResponse(
            session_id=request.session_id,
            answer="\n".join(lines),
            citations=fallback_citations,
            model="local-comparison-fallback",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )

    def _build_graph_state(
        self,
        *,
        request: ChatRequest,
        memory: list[ChatMessage],
        comparison_context: dict[str, Any],
        chunks: list[RetrievedChunk],
    ) -> dict[str, Any]:
        """Shape service data into the state expected by the LangGraph graph."""

        return {
            "session_id": request.session_id,
            "question": request.message,
            "comparison": comparison_context,
            "memory": [message.model_dump(mode="json") for message in memory],
            "retrieved_chunks": [chunk.model_dump(mode="json") for chunk in chunks],
            "citation_rules": [
                "Cite transcript claims using Video A/B chunk labels.",
                "Cite metadata claims using the metadata citation id supplied in comparison context.",
                "Say what evidence is missing instead of inventing metrics or transcript details.",
            ],
        }

    def _extract_answer(self, graph_result: dict[str, Any]) -> str:
        """Pull answer text from common LangGraph result shapes."""

        if not isinstance(graph_result, dict):
            raise GraphExecutionError("LangGraph returned an invalid response type.")

        answer = graph_result.get("answer") or graph_result.get("content") or graph_result.get("final_answer")
        if not isinstance(answer, str) or not answer.strip():
            raise GraphExecutionError("LangGraph did not return an answer.")
        return answer.strip()

    def _extract_citations(
        self,
        graph_result: dict[str, Any],
        chunks: list[RetrievedChunk],
    ) -> list[SourceCitation]:
        """Normalize citations from graph output, falling back to retrieved chunks.

        The graph is allowed to return explicit citation dictionaries. When it
        does not, we still return citations for the retrieved evidence that was
        provided to the model. This makes the API dependable while prompt-level
        citation enforcement is refined.
        """

        raw_citations = graph_result.get("citations", []) if isinstance(graph_result, dict) else []
        citations: list[SourceCitation] = []

        for raw in raw_citations:
            if isinstance(raw, SourceCitation):
                citations.append(raw)
                continue
            if isinstance(raw, dict):
                try:
                    citations.append(SourceCitation(**raw))
                except Exception:
                    logger.warning("Dropping invalid citation from graph", extra={"citation": raw})

        if citations:
            return citations

        # Fallback is deliberately conservative: cite at most top 4 chunks to
        # avoid overwhelming the UI while preserving source traceability.
        return [chunk.to_citation() for chunk in chunks[:4]]


class EchoLangGraphRunner:
    """Development/test LangGraph stand-in.

    This is not a replacement for LangGraph in production. It gives local tests
    and early integration work a deterministic runner while the real compiled
    graph is wired into dependency injection.
    """

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        chunks = state.get("retrieved_chunks", [])
        question = state.get("question", "")
        citations = []
        for chunk in chunks[:2]:
            citations.append(
                {
                    "label": f"Video {chunk.get('video_id')} Chunk {chunk.get('chunk_index')}",
                    "video_id": chunk.get("video_id"),
                    "chunk_id": chunk.get("chunk_id"),
                    "chunk_index": chunk.get("chunk_index"),
                    "platform": chunk.get("platform"),
                    "start_seconds": chunk.get("start_seconds"),
                    "end_seconds": chunk.get("end_seconds"),
                    "text": chunk.get("text", "")[:500],
                    "score": chunk.get("score"),
                }
            )

        return {
            "answer": (
                "I found session-scoped evidence for your question. "
                f"Question: {question}. Use the returned citations to inspect the exact source chunks."
            ),
            "citations": citations,
            "model": "echo-langgraph-runner",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }


async def maybe_await(value: Any) -> Any:
    """Utility for adapting sync test doubles to async protocols."""

    if inspect.isawaitable(value):
        return await value
    return value
