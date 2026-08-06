"""Product create and retrieve API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies.products import get_product_service
from app.schemas.errors import ErrorResponse
from app.schemas.products import ProductCreate, ProductRecord
from app.services.products import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

ERROR_422 = {"model": ErrorResponse, "description": "Request validation failed"}
ERROR_503 = {"model": ErrorResponse, "description": "Product storage unavailable"}


@router.post(
    "",
    response_model=ProductRecord,
    status_code=status.HTTP_201_CREATED,
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
