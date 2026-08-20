"""Read-only Product Intelligence Score detail and history routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.dependencies.catalog_search import get_product_intelligence_read_service
from app.schemas.errors import ErrorResponse
from app.schemas.product_intelligence import (
    ProductIntelligenceScoreDetailResponse,
    ProductIntelligenceScoreHistoryItemResponse,
    ProductIntelligenceScoreHistoryResponse,
)
from app.services.product_intelligence_read import ProductIntelligenceReadService

router = APIRouter(prefix="/products", tags=["Product Intelligence"])

ERROR_404 = {"model": ErrorResponse, "description": "Product or score not found"}
ERROR_503 = {"model": ErrorResponse, "description": "Score storage unavailable"}


@router.get(
    "/{product_id}/intelligence-scores",
    response_model=ProductIntelligenceScoreHistoryResponse,
    status_code=http_status.HTTP_200_OK,
    summary="List Product Intelligence Score history newest first",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid cursor"},
        404: ERROR_404,
        503: ERROR_503,
    },
)
def list_product_intelligence_scores(
    product_id: UUID,
    service: Annotated[
        ProductIntelligenceReadService, Depends(get_product_intelligence_read_service)
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
) -> ProductIntelligenceScoreHistoryResponse:
    page = service.list_history(product_id, limit=limit, cursor=cursor)
    return ProductIntelligenceScoreHistoryResponse(
        items=tuple(
            ProductIntelligenceScoreHistoryItemResponse.from_result(item) for item in page.items
        ),
        next_cursor=page.next_cursor,
    )


@router.get(
    "/{product_id}/intelligence-scores/{score_id}",
    response_model=ProductIntelligenceScoreDetailResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Retrieve one explicit Product Intelligence Score",
    responses={404: ERROR_404, 503: ERROR_503},
)
def retrieve_product_intelligence_score(
    product_id: UUID,
    score_id: UUID,
    service: Annotated[
        ProductIntelligenceReadService, Depends(get_product_intelligence_read_service)
    ],
) -> ProductIntelligenceScoreDetailResponse:
    return ProductIntelligenceScoreDetailResponse.model_validate(
        service.get_score(product_id, score_id)
    )
