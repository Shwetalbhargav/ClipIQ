

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from .schema import VideoAnalyzeRequest, VideoAnalyzeResponse
from .service import VideoIngestionService, get_video_ingestion_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post(
    "/analyze",
    response_model=VideoAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze YouTube and Instagram Reel metadata",
)
async def analyze_videos(
    request: VideoAnalyzeRequest,
    service: VideoIngestionService = Depends(get_video_ingestion_service),
) -> VideoAnalyzeResponse:
    """Analyze submitted video URLs and return normalized metadata only.

    The router deliberately performs no extraction logic. It validates transport
    input through Pydantic, delegates business work to ``VideoIngestionService``,
    and returns a Pydantic response model so the public API contract stays stable.
    """

    try:
        response = await service.analyze_videos([str(url) for url in request.urls])
    except Exception as exc:  # pragma: no cover - service should structure known errors.
        logger.exception("Unhandled failure in video analysis endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected failure while analyzing video URLs.",
        ) from exc

    # If every submitted URL failed validation/extraction, expose that as a client
    # friendly 422 instead of a successful empty analysis. Partial failures still
    # return 200 with structured errors because ClipIQ can compare partial data.
    if response.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[error.model_dump(mode="json") for error in response.errors],
        )

    return response
