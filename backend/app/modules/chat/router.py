"""FastAPI router for ClipIQ chat endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .schema import ChatErrorResponse, ChatRequest, ChatResponse
from .service import ChatService, ChatModuleError, GraphExecutionError, SessionNotReadyError

router = APIRouter(tags=["chat"])


async def get_chat_service(request: Request) -> ChatService:
    """Resolve the ChatService from application state.

    The main FastAPI app should set `app.state.chat_service` during startup.
    Dependency injection keeps this router clean and makes tests simple:
    `app.dependency_overrides[get_chat_service] = lambda: fake_service`.
    """

    service = getattr(request.app.state, "chat_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not configured.",
        )
    return service


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        404: {"model": ChatErrorResponse, "description": "Session not found or not ready"},
        500: {"model": ChatErrorResponse, "description": "Graph execution failure"},
        503: {"model": ChatErrorResponse, "description": "Chat service unavailable"},
    },
    summary="Ask a session-scoped RAG chat question",
)
async def create_chat_turn(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Run one chat turn through the LangGraph-backed orchestration service.

    This endpoint intentionally accepts `session_id` in the body because the
    assignment calls for `POST /chat`. If the app later exposes nested routes,
    this same service can also power `/comparisons/{comparison_id}/chat/stream`.
    """

    try:
        return await service.chat(payload)
    except SessionNotReadyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GraphExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except ChatModuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
