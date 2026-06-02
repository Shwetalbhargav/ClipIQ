"""FastAPI routes for comparison analysis sessions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .schema import ComparisonAnalyzeRequest, ComparisonAnalyzeResponse, ComparisonGetResponse
from .service import ComparisonAnalysisService

router = APIRouter(prefix="/comparisons", tags=["comparisons"])


async def get_analysis_service(request: Request) -> ComparisonAnalysisService:
    service = getattr(request.app.state, "analysis_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Comparison analysis service is not configured.",
        )
    return service


@router.post("", response_model=ComparisonAnalyzeResponse, status_code=status.HTTP_201_CREATED)
async def create_comparison(
    payload: ComparisonAnalyzeRequest,
    service: Annotated[ComparisonAnalysisService, Depends(get_analysis_service)],
) -> ComparisonAnalyzeResponse:
    return await service.analyze(payload)


@router.get("/{comparison_id}", response_model=ComparisonGetResponse)
async def get_comparison(
    comparison_id: str,
    service: Annotated[ComparisonAnalysisService, Depends(get_analysis_service)],
) -> ComparisonGetResponse:
    comparison = await service.get(comparison_id)
    if comparison is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found.")
    return comparison
