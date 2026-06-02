import asyncio

import pytest

from app.modules.memory import InMemoryMemoryRepository, MemoryService, MemoryWindowConfig, MessageRole


def run(coro):
    return asyncio.run(coro)


def make_service() -> MemoryService:
    return MemoryService(InMemoryMemoryRepository())


def test_store_message_persists_role_content_and_metadata():
    service = make_service()

    message = run(
        service.store_message(
            comparison_id="cmp_123",
            role=MessageRole.USER,
            content="  Why did Video A win?  ",
            metadata={"source": "chat"},
        )
    )

    assert message.comparison_id == "cmp_123"
    assert message.role == MessageRole.USER
    assert message.content == "Why did Video A win?"
    assert message.metadata == {"source": "chat"}


def test_retrieve_history_is_scoped_to_comparison_and_chronological():
    service = make_service()

    run(service.store_message(comparison_id="cmp_a", role="user", content="Question A1"))
    run(service.store_message(comparison_id="cmp_b", role="user", content="Question B1"))
    run(service.store_message(comparison_id="cmp_a", role="assistant", content="Answer A1"))

    history = run(service.retrieve_history("cmp_a"))

    assert [message.content for message in history] == ["Question A1", "Answer A1"]
    assert all(message.comparison_id == "cmp_a" for message in history)


def test_retrieve_history_applies_limit_to_recent_messages():
    service = make_service()

    for index in range(5):
        run(service.store_message(comparison_id="cmp_123", role="user", content=f"Message {index}"))

    history = run(service.retrieve_history("cmp_123", limit=2))

    assert [message.content for message in history] == ["Message 3", "Message 4"]


def test_build_context_includes_summary_and_recent_turns():
    service = make_service()

    run(service.set_summary("cmp_123", "User is comparing hook quality and retention."))
    run(service.store_message(comparison_id="cmp_123", role="user", content="Compare the hooks."))
    run(service.store_message(comparison_id="cmp_123", role="assistant", content="Video A opens faster."))

    context = run(service.build_context("cmp_123"))

    assert context.comparison_id == "cmp_123"
    assert context.summary == "User is comparing hook quality and retention."
    assert "Conversation summary:" in context.context_text
    assert "Recent conversation:" in context.context_text
    assert "user: Compare the hooks." in context.context_text
    assert "assistant: Video A opens faster." in context.context_text


def test_build_context_respects_window_and_character_budget():
    service = make_service()

    for index in range(8):
        run(service.store_message(comparison_id="cmp_123", role="user", content=f"Message {index} " + "x" * 80))

    context = run(
        service.build_context(
            "cmp_123",
            config=MemoryWindowConfig(max_messages=3, max_chars=250),
        )
    )

    assert len(context.recent_messages) == 3
    # The structured window keeps the last 3 messages, while the prompt text
    # may clip older text to stay within the character budget.
    assert [message.content.split()[1] for message in context.recent_messages] == ["5", "6", "7"]
    assert "Message 7" in context.context_text
    assert len(context.context_text) <= 282  # includes the truncation marker


def test_empty_content_is_rejected():
    service = make_service()

    with pytest.raises(ValueError, match="message content is required"):
        run(service.store_message(comparison_id="cmp_123", role="user", content="   "))


def test_invalid_role_is_rejected():
    service = make_service()

    with pytest.raises(ValueError):
        run(service.store_message(comparison_id="cmp_123", role="moderator", content="hello"))
