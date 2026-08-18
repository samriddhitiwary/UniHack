"""Read-only catalog projection APIs and explicit readiness application."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi import status as http_status

from app.api.dependencies.catalog import get_publishing_readiness_service
from app.schemas.catalog_projection import CatalogProjectionResponse
from app.schemas.errors import ErrorResponse
from app.schemas.publishing_readiness import (
    ApplyPublishingReadinessRequest,
    CatalogPublishingReadinessResponse,
    PublishingReadinessApplicationResponse,
)
from app.services.publishing_readiness_application import (
    PublishingReadinessApplicationService,
)

router = APIRouter(prefix="/products", tags=["Catalog"])

ERROR_404 = {"model": ErrorResponse, "description": "Product or catalog projection not found"}
ERROR_409 = {"model": ErrorResponse, "description": "Publishing-readiness conflict"}
ERROR_422 = {"model": ErrorResponse, "description": "Request validation failed"}
ERROR_503 = {"model": ErrorResponse, "description": "Product or projection storage unavailable"}


@router.get(
    "/{product_id}/catalog-projections/{projection_id}",
    response_model=CatalogProjectionResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Retrieve a catalog projection",
    responses={404: ERROR_404, 422: ERROR_422, 503: ERROR_503},
)
def retrieve_catalog_projection(
    product_id: UUID,
    projection_id: UUID,
    service: Annotated[
        PublishingReadinessApplicationService, Depends(get_publishing_readiness_service)
    ],
) -> CatalogProjectionResponse:
    projection = service.get_catalog_projection(product_id=product_id, projection_id=projection_id)
    return CatalogProjectionResponse.model_validate(projection)


@router.get(
    "/{product_id}/catalog-projections/{projection_id}/readiness",
    response_model=CatalogPublishingReadinessResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Inspect current publishing readiness",
    responses={404: ERROR_404, 422: ERROR_422, 503: ERROR_503},
)
def retrieve_catalog_publishing_readiness(
    product_id: UUID,
    projection_id: UUID,
    service: Annotated[
        PublishingReadinessApplicationService, Depends(get_publishing_readiness_service)
    ],
) -> CatalogPublishingReadinessResponse:
    state = service.get_publishing_readiness(product_id=product_id, projection_id=projection_id)
    return CatalogPublishingReadinessResponse.model_validate(state)


@router.post(
    "/{product_id}/publishing-readiness/apply",
    response_model=PublishingReadinessApplicationResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Apply an explicit catalog projection's publishing readiness",
    responses={404: ERROR_404, 409: ERROR_409, 422: ERROR_422, 503: ERROR_503},
)
def apply_publishing_readiness(
    product_id: UUID,
    request: ApplyPublishingReadinessRequest,
    service: Annotated[
        PublishingReadinessApplicationService, Depends(get_publishing_readiness_service)
    ],
) -> PublishingReadinessApplicationResponse:
    result = service.apply(
        product_id=product_id,
        projection_id=request.projection_id,
        expected_version=request.version,
    )
    return PublishingReadinessApplicationResponse.model_validate(result)
