"""Product create, list, retrieve, and update API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.dependencies.products import get_product_service
from app.domain.products import ProductStatus
from app.schemas.errors import ErrorResponse
from app.schemas.products import ProductCreate, ProductListResult, ProductRecord, ProductUpdate
from app.services.products import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

ERROR_422 = {"model": ErrorResponse, "description": "Request validation failed"}
ERROR_503 = {"model": ErrorResponse, "description": "Product storage unavailable"}


@router.post(
    "",
    response_model=ProductRecord,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a product",
    description="Create one foundational industrial product with application-managed identity.",
    responses={
        409: {"model": ErrorResponse, "description": "Product already exists"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def create_product(
    request: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRecord:
    return ProductRecord.model_validate(service.create_product(request))


@router.get(
    "",
    response_model=ProductListResult,
    status_code=http_status.HTTP_200_OK,
    summary="List products",
    description="List products newest first with opaque cursor pagination.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid product cursor"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def list_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
    status: ProductStatus | None = None,
) -> ProductListResult:
    return service.list_products(limit=limit, cursor=cursor, status=status)


@router.get(
    "/{product_id}",
    response_model=ProductRecord,
    summary="Retrieve a product",
    description="Retrieve one foundational industrial product by UUID.",
    responses={
        404: {"model": ErrorResponse, "description": "Product not found"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def retrieve_product(
    product_id: UUID,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRecord:
    return ProductRecord.model_validate(service.get_product(product_id))


@router.patch(
    "/{product_id}",
    response_model=ProductRecord,
    status_code=http_status.HTTP_200_OK,
    summary="Update a product",
    description="Partially update an existing product using optimistic concurrency.",
    responses={
        404: {"model": ErrorResponse, "description": "Product not found"},
        409: {"model": ErrorResponse, "description": "Product version conflict"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def update_product(
    product_id: UUID,
    request: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
) -> ProductRecord:
    return ProductRecord.model_validate(service.update_product(product_id, request))
