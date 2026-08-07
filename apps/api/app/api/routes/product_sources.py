"""Product-source text creation API route."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi import status as http_status

from app.api.dependencies.product_sources import get_product_source_service
from app.domain.product_sources.entities import DISPLAY_NAME_MAX_LENGTH
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


@router.post(
    "/upload",
    response_model=ProductSourceRecord,
    status_code=http_status.HTTP_201_CREATED,
    summary="Upload a product source file",
    description="Validate and store one supported file for an existing product.",
    responses={
        404: {"model": ErrorResponse, "description": "Parent product not found"},
        409: {"model": ErrorResponse, "description": "Product source already exists"},
        413: {"model": ErrorResponse, "description": "Product source file too large"},
        422: {"model": ErrorResponse, "description": "Request or file validation failed"},
        503: {
            "model": ErrorResponse,
            "description": "Product, source, or object storage unavailable",
        },
    },
)
def upload_product_source(
    product_id: UUID,
    file: Annotated[UploadFile, File(description="PDF, PNG, JPEG, WEBP, or CSV file")],
    service: Annotated[ProductSourceService, Depends(get_product_source_service)],
    display_name: Annotated[
        str | None, Form(alias="displayName", max_length=DISPLAY_NAME_MAX_LENGTH)
    ] = None,
) -> ProductSourceRecord:
    try:
        source = service.create_file_source(
            product_id=product_id,
            stream=file.file,
            original_filename=file.filename,
            declared_mime_type=file.content_type,
            display_name=display_name,
        )
        return ProductSourceRecord.model_validate(source)
    finally:
        file.file.close()
