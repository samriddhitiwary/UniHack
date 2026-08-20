"""Read-only indexed catalog search and single-Product summary routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.dependencies.catalog_search import (
    get_catalog_search_service,
    get_catalog_summary_service,
)
from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.catalog_search import CatalogProductSearchQuery
from app.domain.product_intelligence import ProductIntelligenceGrade
from app.domain.products import ProductCategory, ProductStatus
from app.schemas.catalog_search import (
    CatalogProductSearchItemResponse,
    CatalogProductSearchResponse,
    CatalogProductSummaryResponse,
)
from app.schemas.errors import ErrorResponse
from app.services.catalog_search import CatalogSearchService
from app.services.catalog_summary import CatalogSummaryService

router = APIRouter(tags=["Catalog Search"])


@router.get(
    "/catalog/products",
    response_model=CatalogProductSearchResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Search the Product catalog through indexed access patterns",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid scoped cursor"},
        422: {"model": ErrorResponse, "description": "Unsupported or invalid filters"},
        503: {"model": ErrorResponse, "description": "Catalog storage unavailable"},
    },
)
def search_catalog_products(
    service: Annotated[CatalogSearchService, Depends(get_catalog_search_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
    category: ProductCategory | None = None,
    status: ProductStatus | None = None,
    manufacturer: Annotated[
        str | None, Query(min_length=1, max_length=200, pattern=r".*\S.*")
    ] = None,
    model_number: Annotated[
        str | None, Query(alias="modelNumber", min_length=1, max_length=200, pattern=r".*\S.*")
    ] = None,
    name_prefix: Annotated[
        str | None, Query(alias="namePrefix", min_length=1, max_length=200, pattern=r".*\S.*")
    ] = None,
    publishing_readiness: Annotated[
        CatalogProjectionStatus | None, Query(alias="publishingReadiness")
    ] = None,
    intelligence_grade: Annotated[
        ProductIntelligenceGrade | None, Query(alias="intelligenceGrade")
    ] = None,
    min_intelligence_score: Annotated[
        int | None, Query(alias="minIntelligenceScore", ge=0, le=100)
    ] = None,
    max_intelligence_score: Annotated[
        int | None, Query(alias="maxIntelligenceScore", ge=0, le=100)
    ] = None,
) -> CatalogProductSearchResponse:
    page = service.search(
        CatalogProductSearchQuery(
            limit=limit,
            cursor=cursor,
            category=category,
            status=status,
            manufacturer=manufacturer,
            model_number=model_number,
            name_prefix=name_prefix,
            publishing_readiness=publishing_readiness,
            intelligence_grade=intelligence_grade,
            min_intelligence_score=min_intelligence_score,
            max_intelligence_score=max_intelligence_score,
        )
    )
    return CatalogProductSearchResponse(
        items=tuple(CatalogProductSearchItemResponse.from_summary(item) for item in page.items),
        next_cursor=page.next_cursor,
    )


@router.get(
    "/products/{product_id}/catalog-summary",
    response_model=CatalogProductSummaryResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Retrieve the latest bounded catalog quality summary",
    responses={
        404: {"model": ErrorResponse, "description": "Product not found"},
        503: {"model": ErrorResponse, "description": "Catalog storage unavailable"},
    },
)
def retrieve_catalog_summary(
    product_id: UUID,
    service: Annotated[CatalogSummaryService, Depends(get_catalog_summary_service)],
) -> CatalogProductSummaryResponse:
    return CatalogProductSummaryResponse.from_summary(service.get_for_product(product_id))
