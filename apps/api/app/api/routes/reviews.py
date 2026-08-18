"""Human product-review API routes."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from fastapi import status as http_status

from app.api.dependencies.product_reviews import get_product_review_service
from app.schemas.errors import ErrorResponse
from app.schemas.product_review import (
    AttributeReviewDecisionCreate,
    AttributeReviewDecisionRecord,
    ProductReviewComplete,
    ProductReviewCreate,
    ProductReviewRecord,
    ReviewDecisionListResult,
)
from app.services.product_review import ProductReviewService

router = APIRouter(prefix="/products/{product_id}/reviews", tags=["Product Reviews"])
ERRORS: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Review resource not found"},
    409: {"model": ErrorResponse, "description": "Review state or version conflict"},
    422: {"model": ErrorResponse, "description": "Review request rejected"},
    503: {"model": ErrorResponse, "description": "Review storage unavailable"},
}


@router.post(
    "",
    response_model=ProductReviewRecord,
    status_code=http_status.HTTP_201_CREATED,
    responses=ERRORS,
)
def create_review(
    product_id: UUID,
    request: ProductReviewCreate,
    service: Annotated[ProductReviewService, Depends(get_product_review_service)],
) -> ProductReviewRecord:
    return ProductReviewRecord.model_validate(
        service.create_review(product_id=product_id, selection_id=request.selection_id)
    )


@router.get("/{review_id}", response_model=ProductReviewRecord, responses=ERRORS)
def get_review(
    product_id: UUID,
    review_id: UUID,
    service: Annotated[ProductReviewService, Depends(get_product_review_service)],
) -> ProductReviewRecord:
    return ProductReviewRecord.model_validate(
        service.get_review(product_id=product_id, review_id=review_id)
    )


@router.get("/{review_id}/decisions", response_model=ReviewDecisionListResult, responses=ERRORS)
def list_review_decisions(
    product_id: UUID,
    review_id: UUID,
    service: Annotated[ProductReviewService, Depends(get_product_review_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
) -> ReviewDecisionListResult:
    page = service.list_decisions(
        product_id=product_id,
        review_id=review_id,
        limit=limit,
        cursor=cursor,
    )
    return ReviewDecisionListResult(
        items=tuple(AttributeReviewDecisionRecord.model_validate(item) for item in page.items),
        next_cursor=page.next_cursor,
    )


@router.post(
    "/{review_id}/attributes/{attribute_name}/decisions",
    response_model=AttributeReviewDecisionRecord,
    status_code=http_status.HTTP_201_CREATED,
    responses=ERRORS,
)
def submit_attribute_decision(
    product_id: UUID,
    review_id: UUID,
    attribute_name: Annotated[
        str, Path(min_length=1, max_length=100, pattern=r"^[A-Za-z][A-Za-z0-9]*$")
    ],
    request: AttributeReviewDecisionCreate,
    service: Annotated[ProductReviewService, Depends(get_product_review_service)],
) -> AttributeReviewDecisionRecord:
    return AttributeReviewDecisionRecord.model_validate(
        service.submit_decision(
            product_id=product_id,
            review_id=review_id,
            attribute_name=attribute_name,
            request=request,
        )
    )


@router.post("/{review_id}/complete", response_model=ProductReviewRecord, responses=ERRORS)
def complete_review(
    product_id: UUID,
    review_id: UUID,
    request: ProductReviewComplete,
    service: Annotated[ProductReviewService, Depends(get_product_review_service)],
) -> ProductReviewRecord:
    return ProductReviewRecord.model_validate(
        service.complete_review(
            product_id=product_id,
            review_id=review_id,
            version=request.version,
            reviewer_id=request.reviewer_id,
        )
    )
