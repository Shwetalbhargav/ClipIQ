"""Streaming service for ClipIQ chat responses.

This module intentionally keeps the Server-Sent Events (SSE) formatting separate
from the FastAPI router. That makes the wire protocol easy to unit test and lets
other delivery layers reuse the same streaming contract later.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

logger = logging.getLogger(__name__)

SSEEventType = Literal["metadata", "delta", "citation", "done", "error"]


class ChatStreamer(Protocol):
    """Protocol expected from the LangGraph chat module.

    The concrete implementation can wrap a LangGraph app, LangChain chain, OpenAI
    SDK stream, Groq stream, or a test double. Keeping the contract narrow avoids
    coupling this streaming module to one graph implementation detail.
    """

    async def stream_chat(
        self,
        *,
        comparison_id: str,
        message: str,
        response_id: str,
        user_id: str | None = None,
    ) -> AsyncIterator[str | dict[str, Any] | "StreamEvent"]:
        """Yield raw stream items from the chat/RAG layer.

        Accepted raw item shapes:
        - ``str``: treated as a token delta.
        - ``dict`` with ``type`` or ``event``: normalized into frontend SSE.
        - ``StreamEvent``: passed through after validation.
        """
        ...


@dataclass(slots=True)
class StreamEvent:
    """Normalized event emitted over SSE.

    ``data`` must be JSON serializable because it is sent as the SSE ``data``
    payload. The router emits ``event: <type>`` plus the JSON payload, so React can
    consume it via EventSource-style handlers or fetch-stream parsing.
    """

    type: SSEEventType
    data: dict[str, Any] = field(default_factory=dict)


class StreamingServiceError(RuntimeError):
    """Raised when the streaming service cannot satisfy a chat request."""


class StreamingService:
    """Turns LangGraph/chat-token output into frontend-compatible SSE events."""

    def __init__(self, chat_streamer: ChatStreamer, *, model_name: str = "gpt-4o-mini") -> None:
        self.chat_streamer = chat_streamer
        self.model_name = model_name

    async def stream_response(
        self,
        *,
        comparison_id: str,
        message: str,
        user_id: str | None = None,
        is_disconnected: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[str]:
        """Yield encoded SSE frames for a single chat response.

        The stream is defensive by design:
        - validation errors are returned as ``error`` events instead of raw 500s;
        - client disconnects stop upstream iteration quickly;
        - unexpected exceptions are logged server-side and converted to a safe
          terminal ``error`` event for the browser.
        """

        response_id = f"resp_{uuid.uuid4().hex}"
        started_at = _utc_now_iso()

        try:
            _validate_request(comparison_id=comparison_id, message=message)

            yield encode_sse(
                StreamEvent(
                    type="metadata",
                    data={
                        "type": "metadata",
                        "response_id": response_id,
                        "comparison_id": comparison_id,
                        "model": self.model_name,
                        "started_at": started_at,
                    },
                )
            )

            token_count = 0
            citation_count = 0

            async for raw_item in self.chat_streamer.stream_chat(
                comparison_id=comparison_id,
                message=message,
                response_id=response_id,
                user_id=user_id,
            ):
                if is_disconnected is not None and await is_disconnected():
                    logger.info("SSE client disconnected", extra={"comparison_id": comparison_id})
                    break

                event = normalize_stream_item(raw_item)
                if event is None:
                    continue

                if event.type == "delta":
                    token_count += 1
                elif event.type == "citation":
                    citation_count += 1

                yield encode_sse(event)

            # A final done event gives the frontend a reliable place to stop its
            # loading indicator even if the model produced no citations.
            yield encode_sse(
                StreamEvent(
                    type="done",
                    data={
                        "type": "done",
                        "response_id": response_id,
                        "status": "completed",
                        "usage": {
                            "streamed_delta_count": token_count,
                            "citation_count": citation_count,
                        },
                    },
                )
            )

        except StreamingServiceError as exc:
            yield encode_sse(_safe_error_event(response_id=response_id, code="bad_request", message=str(exc)))
        except asyncio.CancelledError:
            # ASGI servers cancel generators during disconnect/shutdown. Re-raise
            # so FastAPI can clean up the response task correctly.
            raise
        except Exception as exc:  # pragma: no cover - log branch is still valuable in prod
            logger.exception("Streaming response failed", extra={"comparison_id": comparison_id})
            yield encode_sse(
                _safe_error_event(
                    response_id=response_id,
                    code="stream_failed",
                    message="The response stream failed before completion. Please retry.",
                    detail=exc.__class__.__name__,
                )
            )


def normalize_stream_item(raw_item: str | dict[str, Any] | StreamEvent | None) -> StreamEvent | None:
    """Normalize model/graph output into the SSE contract.

    The chat module can yield simple token strings during LLM streaming, then
    structured dictionaries for citations or provider usage. This function keeps
    that flexibility while ensuring the browser only receives known event types.
    """

    if raw_item is None:
        return None

    if isinstance(raw_item, StreamEvent):
        return raw_item

    if isinstance(raw_item, str):
        if raw_item == "":
            return None
        return StreamEvent(type="delta", data={"type": "delta", "text": raw_item})

    if not isinstance(raw_item, dict):
        raise StreamingServiceError(f"Unsupported stream item type: {type(raw_item).__name__}")

    event_type = raw_item.get("type") or raw_item.get("event")
    if event_type == "token":
        event_type = "delta"

    if event_type not in {"metadata", "delta", "citation", "done", "error"}:
        raise StreamingServiceError(f"Unsupported stream event type: {event_type!r}")

    data = dict(raw_item.get("data") or raw_item)
    data["type"] = event_type

    # Normalize common LLM provider token shapes into one frontend field.
    if event_type == "delta" and "text" not in data:
        data["text"] = data.get("delta") or data.get("content") or ""

    return StreamEvent(type=event_type, data=data)  # type: ignore[arg-type]


def encode_sse(event: StreamEvent) -> str:
    """Encode a normalized event as an SSE frame.

    SSE supports multiline ``data:`` fields. Compact JSON keeps the frontend parser
    simple and makes tests deterministic.
    """

    event_name = _sanitize_event_name(event.type)
    payload = json.dumps(event.data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event_name}\ndata: {payload}\n\n"


def _safe_error_event(
    *,
    response_id: str,
    code: str,
    message: str,
    detail: str | None = None,
) -> StreamEvent:
    """Build a safe error payload that does not leak secrets or stack traces."""

    data: dict[str, Any] = {
        "type": "error",
        "response_id": response_id,
        "status": "failed",
        "error": {"code": code, "message": message},
    }
    if detail:
        data["error"]["detail"] = detail
    return StreamEvent(type="error", data=data)


def _sanitize_event_name(event_type: str) -> str:
    """Protect the SSE frame from accidental newline/header injection."""

    if not re.fullmatch(r"[a-z_]+", event_type):
        raise StreamingServiceError(f"Invalid SSE event name: {event_type!r}")
    return event_type


def _validate_request(*, comparison_id: str, message: str) -> None:
    """Validate user-controlled request fields before invoking the chat graph."""

    if not comparison_id or not comparison_id.strip():
        raise StreamingServiceError("comparison_id is required")
    if not message or not message.strip():
        raise StreamingServiceError("message is required")
    if len(message) > 8_000:
        raise StreamingServiceError("message is too long; keep it under 8,000 characters")


def _utc_now_iso() -> str:
    """Return an ISO timestamp without adding a heavyweight dependency."""

    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()
