"""Product-source text creation API route."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.dependencies.product_sources import get_product_source_service
from app.schemas.errors import ErrorResponse
from app.schemas.product_sources import ProductSourceRecord, TextProductSourceCreate
from app.services.product_sources import ProductSourceService

router = APIRouter(prefix="/products/{product_id}/sources", tags=["Product Sources"])


@router.post(
    "/text",
    response_model=ProductSourceRecord,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a text product source",
    description="Attach normalized plain text to an existing product as a ready source.",
    responses={
        404: {"model": ErrorResponse, "description": "Parent product not found"},
        409: {"model": ErrorResponse, "description": "Product source already exists"},
        422: {"model": ErrorResponse, "description": "Request validation failed"},
        503: {"model": ErrorResponse, "description": "Product or source storage unavailable"},
    },
)
def create_text_source(
    product_id: UUID,
    request: TextProductSourceCreate,
    service: Annotated[ProductSourceService, Depends(get_product_source_service)],
) -> ProductSourceRecord:
    return ProductSourceRecord.model_validate(service.create_text_source(product_id, request))
