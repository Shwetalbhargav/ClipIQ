"""Schemas for ClipIQ conversation memory.

The memory module is intentionally small: it stores chat turns scoped to a
single comparison/session and returns a compact context block for LangGraph.
Keeping these DTOs separate from the persistence implementation makes the
memory flow easy to test and easy to swap from an in-memory repository to
MongoDB/Motor in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class MessageRole(str, Enum):
    """Allowed roles stored in chat history."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class MemoryMessageCreate:
    """Input object used when appending a message to memory."""

    comparison_id: str
    role: MessageRole | str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MemoryMessage:
    """Persisted chat message returned by the memory repository/service."""

    id: str
    comparison_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, payload: MemoryMessageCreate) -> "MemoryMessage":
        role = MessageRole(payload.role)
        content = payload.content.strip()
        if not payload.comparison_id.strip():
            raise ValueError("comparison_id is required")
        if not content:
            raise ValueError("message content is required")

        return cls(
            id=str(uuid4()),
            comparison_id=payload.comparison_id.strip(),
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
            metadata=dict(payload.metadata or {}),
        )

    def to_prompt_line(self) -> str:
        """Render one memory turn in a stable format for prompt assembly."""

        return f"{self.role.value}: {self.content}"


@dataclass(frozen=True, slots=True)
class ConversationContext:
    """Context payload consumed by the LangGraph chat state.

    `context_text` is the compact prompt-ready representation. The structured
    fields remain available for graph nodes that need role-aware messages.
    """

    comparison_id: str
    recent_messages: list[MemoryMessage]
    summary: str | None
    context_text: str


@dataclass(frozen=True, slots=True)
class MemoryWindowConfig:
    """Controls how much chat history is included in the model prompt."""

    max_messages: int = 6
    max_chars: int = 4_000
    include_summary: bool = True

    def __post_init__(self) -> None:
        if self.max_messages < 1:
            raise ValueError("max_messages must be at least 1")
        if self.max_chars < 200:
            raise ValueError("max_chars must be at least 200")
