"""FastAPI router for Module 9: Streaming.

Mount this router in the main FastAPI app with:

    from modules.streaming.router import router as streaming_router
    app.include_router(streaming_router)

The endpoint intentionally uses POST instead of EventSource GET because chat
messages have a JSON body. The React frontend can consume it with ``fetch`` and a
ReadableStream parser while still receiving standards-compliant SSE frames.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .service import StreamingService

router = APIRouter(prefix="/api/comparisons", tags=["streaming"])

_streaming_service: StreamingService | None = None


class ChatStreamRequest(BaseModel):
    """Request body for a streamed chat turn."""

    message: str = Field(..., min_length=1, max_length=8_000, description="User question to answer with RAG")
    user_id: str | None = Field(default=None, description="Optional authenticated user id for scoped memory")


class MissingStreamingServiceError(RuntimeError):
    """Raised when the app forgot to register the real streaming service."""


def set_streaming_service(service: StreamingService) -> None:
    """Register the concrete service at application startup.

    This small setter keeps the router framework-native and makes tests painless:
    tests can inject a fake chat streamer without importing the whole LangGraph
    stack or touching environment variables.
    """

    global _streaming_service
    _streaming_service = service


async def get_streaming_service(request: Request) -> StreamingService:
    """Resolve the streaming service from app state."""

    service = getattr(request.app.state, "streaming_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="StreamingService has not been configured",
        )
    return service


@router.post("/{comparison_id}/chat/stream")
async def stream_chat_response(
    comparison_id: str,
    payload: ChatStreamRequest,
    request: Request,
    service: Annotated[StreamingService, Depends(get_streaming_service)],
) -> StreamingResponse:
    """Stream a source-grounded answer as Server-Sent Events.

    Frontend event contract:
    - ``metadata``: response/model/session metadata.
    - ``delta``: token text, append ``data.text`` to the assistant bubble.
    - ``citation``: render source chips/list items while or after text streams.
    - ``done``: stop loading indicators and persist final UI state.
    - ``error``: show retryable failure message.
    """

    try:
        event_stream = service.stream_response(
            comparison_id=comparison_id,
            message=payload.message,
            user_id=payload.user_id,
            is_disconnected=request.is_disconnected,
        )
    except MissingStreamingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            # Prevent proxies and browsers from buffering token deltas.
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
