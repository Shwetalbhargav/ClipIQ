"""LangGraph node implementations for ClipIQ comparison chat.

Each node is a small async callable. External systems are injected through the
`GraphDependencies` dataclass so the graph can be tested without MongoDB,
Qdrant, or an LLM provider running locally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .state import Citation, ComparisonSummary, GraphState, RetrievedChunk, VideoLabel, VideoMetadata


class Retriever(Protocol):
    """Vector retrieval adapter.

    Production implementation should call Qdrant/Chroma with a filter like:
    `comparison_id == state["comparison_id"] AND video_id == "A" | "B"`.
    """

    async def retrieve(
        self,
        *,
        comparison_id: str,
        video_id: VideoLabel,
        query: str,
        top_k: int,
    ) -> list[RetrievedChunk]: ...


class MetadataRepository(Protocol):
    """Repository adapter for normalized video metadata and metrics."""

    async def get_video_metadata(self, *, comparison_id: str) -> dict[VideoLabel, VideoMetadata]: ...


class MemoryRepository(Protocol):
    """Repository adapter for chat history scoped to a comparison/session."""

    async def get_recent_messages(self, *, comparison_id: str, limit: int = 6) -> list[dict[str, str]]: ...

    async def append_message(self, *, comparison_id: str, role: str, content: str) -> None: ...


class ResponseGenerator(Protocol):
    """LLM adapter used by the response node.

    Production can wrap GPT-4o-mini/Groq/Llama. Tests can provide a deterministic
    fake generator that asserts the prompt contains metadata and citations.
    """

    async def generate(self, *, question: str, context: str, memory: list[dict[str, str]]) -> str: ...


@dataclass(slots=True)
class GraphDependencies:
    """Services required by graph nodes."""

    retriever: Retriever
    metadata_repo: MetadataRepository
    memory_repo: MemoryRepository
    response_generator: ResponseGenerator
    top_k_per_video: int = 4


def _errors(state: GraphState, message: str) -> list[str]:
    return [*state.get("errors", []), message]


def _format_number(value: int | float | None) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.2f}"
    return f"{value:,}"


def _safe_text(text: str, max_chars: int = 900) -> str:
    text = " ".join(text.split())
    return text if len(text) <= max_chars else text[: max_chars - 1].rstrip() + "…"


def _chunk_to_citation(chunk: RetrievedChunk) -> Citation:
    """Convert retrieved evidence into a stable frontend citation object."""

    video_id = chunk.get("video_id", "A")
    chunk_index = int(chunk.get("chunk_index", 0))
    return {
        "citation_id": f"Video {video_id} Chunk {chunk_index}",
        "video_id": video_id,
        "chunk_id": chunk.get("chunk_id", f"{video_id}-{chunk_index}"),
        "chunk_index": chunk_index,
        "platform": chunk.get("platform", "unknown"),
        "source_url": chunk.get("source_url", ""),
        "start_seconds": chunk.get("start_seconds"),
        "end_seconds": chunk.get("end_seconds"),
        "text": _safe_text(chunk.get("text", ""), 280),
    }


def create_load_memory_node(deps: GraphDependencies):
    """Node: load prior conversation turns for follow-up awareness.

    This node keeps memory scoped to `comparison_id`; it should never fetch global
    history. For cost control, the repo should return a short recent window or a
    rolling summary plus last N messages.
    """

    async def load_memory(state: GraphState) -> dict[str, Any]:
        memory = await deps.memory_repo.get_recent_messages(
            comparison_id=state["comparison_id"],
            limit=6,
        )
        return {"memory": memory}

    return load_memory


def create_retrieve_a_node(deps: GraphDependencies):
    """Node: retrieve transcript evidence for Video A.

    The adapter must filter by both comparison/session ID and `video_id='A'`.
    Keeping Video A and Video B retrieval as separate nodes makes source coverage
    obvious in traces and easier to debug in demos.
    """

    async def retrieve_a(state: GraphState) -> dict[str, Any]:
        chunks = await deps.retriever.retrieve(
            comparison_id=state["comparison_id"],
            video_id="A",
            query=state["question"],
            top_k=deps.top_k_per_video,
        )
        return {"retrieved_a": chunks}

    return retrieve_a


def create_retrieve_b_node(deps: GraphDependencies):
    """Node: retrieve transcript evidence for Video B.

    This mirrors Video A retrieval but enforces `video_id='B'`, preventing the LLM
    from accidentally treating one video's transcript as evidence for the other.
    """

    async def retrieve_b(state: GraphState) -> dict[str, Any]:
        chunks = await deps.retriever.retrieve(
            comparison_id=state["comparison_id"],
            video_id="B",
            query=state["question"],
            top_k=deps.top_k_per_video,
        )
        return {"retrieved_b": chunks}

    return retrieve_b


def create_fetch_metadata_node(deps: GraphDependencies):
    """Node: fetch structured metadata and engagement metrics.

    Transcript retrieval answers content questions; metadata answers factual metric
    questions like views, likes, comments, creator, follower count, duration, and
    engagement rate. Missing values stay unavailable instead of being fabricated.
    """

    async def fetch_metadata(state: GraphState) -> dict[str, Any]:
        metadata = await deps.metadata_repo.get_video_metadata(comparison_id=state["comparison_id"])
        missing = [video_id for video_id in ("A", "B") if video_id not in metadata]
        if missing:
            return {
                "metadata": metadata,
                "errors": _errors(state, f"Missing metadata for video(s): {', '.join(missing)}"),
            }
        return {"metadata": metadata}

    return fetch_metadata


def create_compare_node(_deps: GraphDependencies):
    """Node: deterministically compare metrics before generation.

    The LLM should not calculate core metrics from scratch if the backend already
    persisted them. This node computes a compact comparison summary that the model
    can quote safely alongside transcript evidence.
    """

    async def compare(state: GraphState) -> dict[str, Any]:
        metadata = state.get("metadata", {})
        a = metadata.get("A", {})
        b = metadata.get("B", {})
        rate_a = a.get("engagement_rate")
        rate_b = b.get("engagement_rate")

        notes: list[str] = []
        winner: VideoLabel | None = None
        delta: float | None = None

        if rate_a is None or rate_b is None:
            notes.append("Engagement-rate comparison is limited because one or both rates are unavailable.")
        else:
            delta = round(abs(float(rate_a) - float(rate_b)), 4)
            if float(rate_a) > float(rate_b):
                winner = "A"
            elif float(rate_b) > float(rate_a):
                winner = "B"
            else:
                notes.append("Both videos have the same engagement rate.")

        summary: ComparisonSummary = {
            "winner_by_engagement_rate": winner,
            "engagement_rate_delta": delta,
            "metadata_notes": notes,
        }
        return {"comparison": summary}

    return compare


def create_build_context_node(_deps: GraphDependencies):
    """Node: build the grounded prompt context and citation list.

    The context is deliberately plain text so any chat model can consume it. Each
    transcript excerpt includes a citation label like `[Video A Chunk 0]`, which
    the generator is instructed to reference in its answer.
    """

    async def build_context(state: GraphState) -> dict[str, Any]:
        metadata = state.get("metadata", {})
        retrieved = [*state.get("retrieved_a", []), *state.get("retrieved_b", [])]
        citations = [_chunk_to_citation(chunk) for chunk in retrieved]

        metadata_lines = ["STRUCTURED METADATA"]
        for video_id in ("A", "B"):
            item = metadata.get(video_id, {})
            metadata_lines.append(
                " | ".join(
                    [
                        f"Video {video_id}",
                        f"platform={item.get('platform', 'unknown')}",
                        f"creator={item.get('creator') or 'unavailable'}",
                        f"followers={_format_number(item.get('follower_count'))}",
                        f"views={_format_number(item.get('views'))}",
                        f"likes={_format_number(item.get('likes'))}",
                        f"comments={_format_number(item.get('comments'))}",
                        f"engagement_rate={_format_number(item.get('engagement_rate'))}%",
                        f"duration_seconds={_format_number(item.get('duration_seconds'))}",
                        f"hashtags={', '.join(item.get('hashtags', [])) or 'unavailable'}",
                    ]
                )
            )

        comparison = state.get("comparison", {})
        comparison_lines = [
            "DETERMINISTIC COMPARISON",
            f"winner_by_engagement_rate={comparison.get('winner_by_engagement_rate') or 'tie_or_unavailable'}",
            f"engagement_rate_delta={_format_number(comparison.get('engagement_rate_delta'))}",
        ]
        for note in comparison.get("metadata_notes", []):
            comparison_lines.append(f"note={note}")

        transcript_lines = ["RETRIEVED TRANSCRIPT EVIDENCE"]
        if not citations:
            transcript_lines.append("No transcript chunks were retrieved. Use metadata only and say evidence is limited.")
        for citation in citations:
            transcript_lines.append(
                f"[{citation['citation_id']}] {citation.get('text', '')}"
            )

        context = "\n".join([*metadata_lines, "", *comparison_lines, "", *transcript_lines])
        return {"context": context, "citations": citations}

    return build_context


def create_generate_response_node(deps: GraphDependencies):
    """Node: generate the final grounded answer.

    The generator gets only the user question, compact memory, and the prepared
    evidence context. Prompt construction inside the generator should require
    citations for transcript claims and state when evidence is unavailable.
    """

    async def generate_response(state: GraphState) -> dict[str, Any]:
        answer = await deps.response_generator.generate(
            question=state["question"],
            context=state.get("context", ""),
            memory=state.get("memory", []),
        )
        return {"answer": answer}

    return generate_response


def create_persist_turn_node(deps: GraphDependencies):
    """Node: persist user and assistant turns after successful generation.

    Persistence is last so failed retrieval or generation does not create a fake
    assistant turn. The chat endpoint may also persist the user message before
    streaming; in that setup, replace this node with assistant-only persistence.
    """

    async def persist_turn(state: GraphState) -> dict[str, Any]:
        await deps.memory_repo.append_message(
            comparison_id=state["comparison_id"],
            role="user",
            content=state["question"],
        )
        await deps.memory_repo.append_message(
            comparison_id=state["comparison_id"],
            role="assistant",
            content=state.get("answer", ""),
        )
        return {}

    return persist_turn
