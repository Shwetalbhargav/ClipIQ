"""Conversation memory service for ClipIQ.

Memory flow:
1. The chat endpoint stores the incoming user message before generation.
2. LangGraph calls `build_context()` to load session-scoped recent turns.
3. The generation node uses the returned `context_text` alongside retrieved
   transcript chunks and structured video metadata.
4. After streaming completes, the assistant message is persisted with optional
   citation/usage metadata.

The service depends on a repository protocol instead of a concrete database.
That keeps the module clean: production can use MongoDB, tests can use the
in-memory repository below, and LangGraph only talks to the service boundary.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Protocol

from .schema import (
    ConversationContext,
    MemoryMessage,
    MemoryMessageCreate,
    MemoryWindowConfig,
    MessageRole,
)


class MemoryRepository(Protocol):
    """Persistence contract for chat memory.

    A MongoDB implementation should store documents in `chat_messages` with an
    index on `(comparison_id, created_at)`. The service only requires append and
    session-scoped reads, which makes it safe for replacement later.
    """

    async def append(self, message: MemoryMessage) -> MemoryMessage:
        ...

    async def list_by_comparison(
        self,
        comparison_id: str,
        *,
        limit: int | None = None,
    ) -> list[MemoryMessage]:
        ...

    async def get_summary(self, comparison_id: str) -> str | None:
        ...

    async def set_summary(self, comparison_id: str, summary: str | None) -> None:
        ...


class InMemoryMemoryRepository:
    """Small repository for unit tests and local development.

    It intentionally mirrors the production access pattern: append-only writes,
    chronological reads, and an optional per-session rolling summary.
    """

    def __init__(self) -> None:
        self._messages: dict[str, list[MemoryMessage]] = defaultdict(list)
        self._summaries: dict[str, str] = {}

    async def append(self, message: MemoryMessage) -> MemoryMessage:
        self._messages[message.comparison_id].append(message)
        self._messages[message.comparison_id].sort(key=lambda item: item.created_at)
        return message

    async def list_by_comparison(
        self,
        comparison_id: str,
        *,
        limit: int | None = None,
    ) -> list[MemoryMessage]:
        messages = list(self._messages.get(comparison_id, []))
        if limit is not None:
            messages = messages[-limit:]
        return messages

    async def get_summary(self, comparison_id: str) -> str | None:
        return self._summaries.get(comparison_id)

    async def set_summary(self, comparison_id: str, summary: str | None) -> None:
        if summary:
            self._summaries[comparison_id] = summary.strip()
        else:
            self._summaries.pop(comparison_id, None)


class MemoryService:
    """Application service for storing and preparing conversation memory."""

    def __init__(self, repository: MemoryRepository) -> None:
        self._repo = repository

    async def store_message(
        self,
        *,
        comparison_id: str,
        role: MessageRole | str,
        content: str,
        metadata: dict | None = None,
    ) -> MemoryMessage:
        """Persist one chat message for a comparison/session.

        The comparison ID is the memory boundary. This prevents a creator's
        follow-up question in one video comparison from leaking into another.
        """

        message = MemoryMessage.new(
            MemoryMessageCreate(
                comparison_id=comparison_id,
                role=role,
                content=content,
                metadata=metadata or {},
            )
        )
        return await self._repo.append(message)

    async def store_turn(
        self,
        *,
        comparison_id: str,
        user_message: str,
        assistant_message: str,
        assistant_metadata: dict | None = None,
    ) -> tuple[MemoryMessage, MemoryMessage]:
        """Persist a complete user/assistant exchange in order."""

        user = await self.store_message(
            comparison_id=comparison_id,
            role=MessageRole.USER,
            content=user_message,
        )
        assistant = await self.store_message(
            comparison_id=comparison_id,
            role=MessageRole.ASSISTANT,
            content=assistant_message,
            metadata=assistant_metadata,
        )
        return user, assistant

    async def retrieve_history(
        self,
        comparison_id: str,
        *,
        limit: int | None = None,
    ) -> list[MemoryMessage]:
        """Return chronological chat history for a single comparison."""

        if not comparison_id.strip():
            raise ValueError("comparison_id is required")
        return await self._repo.list_by_comparison(comparison_id.strip(), limit=limit)

    async def set_summary(self, comparison_id: str, summary: str | None) -> None:
        """Save a rolling memory summary for older turns.

        Summaries should be generated by a separate summarization node once the
        conversation grows. This service simply stores and injects them.
        """

        if not comparison_id.strip():
            raise ValueError("comparison_id is required")
        await self._repo.set_summary(comparison_id.strip(), summary)

    async def build_context(
        self,
        comparison_id: str,
        *,
        config: MemoryWindowConfig | None = None,
    ) -> ConversationContext:
        """Build compact prompt context from chat memory.

        Recent messages are kept verbatim because follow-up questions often
        depend on exact wording. Older context should live in a rolling summary
        to control token cost; factual claims still come from retrieval.
        """

        cfg = config or MemoryWindowConfig()
        normalized_comparison_id = comparison_id.strip()
        if not normalized_comparison_id:
            raise ValueError("comparison_id is required")

        recent_messages = await self.retrieve_history(
            normalized_comparison_id,
            limit=cfg.max_messages,
        )
        summary = await self._repo.get_summary(normalized_comparison_id)
        if not cfg.include_summary:
            summary = None

        context_text = self._format_context(
            summary=summary,
            messages=recent_messages,
            max_chars=cfg.max_chars,
        )

        return ConversationContext(
            comparison_id=normalized_comparison_id,
            recent_messages=recent_messages,
            summary=summary,
            context_text=context_text,
        )

    @staticmethod
    def _format_context(
        *,
        summary: str | None,
        messages: list[MemoryMessage],
        max_chars: int,
    ) -> str:
        sections: list[str] = []
        if summary:
            sections.append(f"Conversation summary:\n{summary.strip()}")

        if messages:
            rendered_messages = "\n".join(message.to_prompt_line() for message in messages)
            sections.append(f"Recent conversation:\n{rendered_messages}")

        if not sections:
            return "No prior conversation memory for this comparison."

        context = "\n\n".join(sections)
        if len(context) <= max_chars:
            return context

        # Preserve the end of the context because the latest turns usually hold
        # pronouns and follow-up intent, e.g. "make that suggestion more tactical".
        clipped = context[-max_chars:]
        return f"[conversation memory truncated]\n{clipped}"


class MongoMemoryRepository:
    """MongoDB/Motor-backed repository adapter.

    Expected collections:
    - `chat_messages`: append-only chat turns
    - `chat_memory_summaries`: one rolling summary per comparison

    The adapter is included here so production code has a clear integration
    path, while tests can stay fast with `InMemoryMemoryRepository`.
    """

    def __init__(self, db) -> None:  # db is typically `motor.motor_asyncio.AsyncIOMotorDatabase`
        self._messages = db["chat_messages"]
        self._summaries = db["chat_memory_summaries"]

    async def append(self, message: MemoryMessage) -> MemoryMessage:
        await self._messages.insert_one(self._to_document(message))
        return message

    async def list_by_comparison(
        self,
        comparison_id: str,
        *,
        limit: int | None = None,
    ) -> list[MemoryMessage]:
        cursor = self._messages.find({"comparison_id": comparison_id}).sort("created_at", 1)
        if limit is not None:
            # Mongo cannot efficiently return the last N while preserving ascending
            # order without either reverse sorting or an aggregation. For chat
            # memory windows this query is small and explicit.
            docs = await cursor.to_list(length=None)
            docs = docs[-limit:]
        else:
            docs = await cursor.to_list(length=None)
        return [self._from_document(doc) for doc in docs]

    async def get_summary(self, comparison_id: str) -> str | None:
        doc = await self._summaries.find_one({"comparison_id": comparison_id})
        return None if not doc else doc.get("summary")

    async def set_summary(self, comparison_id: str, summary: str | None) -> None:
        if not summary:
            await self._summaries.delete_one({"comparison_id": comparison_id})
            return
        await self._summaries.update_one(
            {"comparison_id": comparison_id},
            {
                "$set": {
                    "comparison_id": comparison_id,
                    "summary": summary.strip(),
                    "updated_at": datetime.utcnow(),
                }
            },
            upsert=True,
        )

    @staticmethod
    def _to_document(message: MemoryMessage) -> dict:
        return {
            "_id": message.id,
            "comparison_id": message.comparison_id,
            "role": message.role.value,
            "content": message.content,
            "created_at": message.created_at,
            "metadata": message.metadata,
        }

    @staticmethod
    def _from_document(doc: dict) -> MemoryMessage:
        return MemoryMessage(
            id=str(doc.get("_id")),
            comparison_id=doc["comparison_id"],
            role=MessageRole(doc["role"]),
            content=doc["content"],
            created_at=doc["created_at"],
            metadata=dict(doc.get("metadata") or {}),
        )
