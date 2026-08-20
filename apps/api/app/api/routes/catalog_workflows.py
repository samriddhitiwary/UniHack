"""Catalog Intelligence workflow start, read, history, and resume routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies.catalog_workflows import get_catalog_workflow_service
from app.domain.catalog_workflow import CatalogIntelligenceWorkflowConfiguration
from app.schemas.catalog_workflow import (
    CatalogWorkflowConfigurationRequest,
    CatalogWorkflowHistoryResponse,
    CatalogWorkflowResponse,
    CatalogWorkflowResumeRequest,
)
from app.schemas.errors import ErrorResponse
from app.services.catalog_workflow_orchestrator import CatalogIntelligenceWorkflowService

router = APIRouter(prefix="/products/{product_id}/workflows", tags=["Catalog Workflows"])


@router.post(
    "",
    response_model=CatalogWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
def start_workflow(
    product_id: UUID,
    request: CatalogWorkflowConfigurationRequest,
    service: Annotated[CatalogIntelligenceWorkflowService, Depends(get_catalog_workflow_service)],
) -> CatalogWorkflowResponse:
    workflow = service.start(
        product_id=product_id,
        configuration=CatalogIntelligenceWorkflowConfiguration(
            **request.model_dump(by_alias=False)
        ),
    )
    return CatalogWorkflowResponse.from_domain(workflow)


@router.get("", response_model=CatalogWorkflowHistoryResponse)
def list_workflows(
    product_id: UUID,
    service: Annotated[CatalogIntelligenceWorkflowService, Depends(get_catalog_workflow_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
) -> CatalogWorkflowHistoryResponse:
    return CatalogWorkflowHistoryResponse.from_domain(
        service.list(product_id=product_id, limit=limit, cursor=cursor)
    )


@router.get("/{workflow_id}", response_model=CatalogWorkflowResponse)
def get_workflow(
    product_id: UUID,
    workflow_id: UUID,
    service: Annotated[CatalogIntelligenceWorkflowService, Depends(get_catalog_workflow_service)],
) -> CatalogWorkflowResponse:
    return CatalogWorkflowResponse.from_domain(
        service.get(product_id=product_id, workflow_id=workflow_id)
    )


@router.post("/{workflow_id}/resume", response_model=CatalogWorkflowResponse)
def resume_workflow(
    product_id: UUID,
    workflow_id: UUID,
    request: CatalogWorkflowResumeRequest,
    service: Annotated[CatalogIntelligenceWorkflowService, Depends(get_catalog_workflow_service)],
) -> CatalogWorkflowResponse:
    return CatalogWorkflowResponse.from_domain(
        service.resume(
            product_id=product_id,
            workflow_id=workflow_id,
            expected_version=request.version,
        )
    )
