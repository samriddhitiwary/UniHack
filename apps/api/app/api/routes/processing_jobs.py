"""Processing-job creation and read API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status

from app.api.dependencies.processing_jobs import get_processing_job_service
from app.schemas.errors import ErrorResponse
from app.schemas.processing_jobs import (
    ProcessingJobCreateRequest,
    ProcessingJobListResult,
    ProcessingJobRecord,
)
from app.services.processing_jobs import ProcessingJobService

router = APIRouter(tags=["Processing Jobs"])

ERROR_422 = {"model": ErrorResponse, "description": "Request validation failed"}
ERROR_503 = {"model": ErrorResponse, "description": "Required storage unavailable"}


@router.post(
    "/products/{product_id}/sources/{source_id}/jobs",
    response_model=ProcessingJobRecord,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a processing job",
    description="Create one compatible pending job without starting processing.",
    responses={
        404: {"model": ErrorResponse, "description": "Parent product or source not found"},
        409: {"model": ErrorResponse, "description": "Processing job already exists"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def create_processing_job(
    product_id: UUID,
    source_id: UUID,
    request: ProcessingJobCreateRequest,
    service: Annotated[ProcessingJobService, Depends(get_processing_job_service)],
) -> ProcessingJobRecord:
    return ProcessingJobRecord.model_validate(
        service.create_job(
            product_id=product_id,
            source_id=source_id,
            job_type=request.job_type,
        )
    )


@router.get(
    "/processing-jobs/{job_id}",
    response_model=ProcessingJobRecord,
    status_code=http_status.HTTP_200_OK,
    summary="Retrieve a processing job",
    description="Retrieve one safe processing-job record by UUID.",
    responses={
        404: {"model": ErrorResponse, "description": "Processing job not found"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def retrieve_processing_job(
    job_id: UUID,
    service: Annotated[ProcessingJobService, Depends(get_processing_job_service)],
) -> ProcessingJobRecord:
    return ProcessingJobRecord.model_validate(service.get_job(job_id=job_id))


@router.get(
    "/products/{product_id}/processing-jobs",
    response_model=ProcessingJobListResult,
    status_code=http_status.HTTP_200_OK,
    summary="List product processing jobs",
    description="List one product's jobs newest first with opaque pagination.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid processing-job cursor"},
        404: {"model": ErrorResponse, "description": "Parent product not found"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def list_product_processing_jobs(
    product_id: UUID,
    service: Annotated[ProcessingJobService, Depends(get_processing_job_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
) -> ProcessingJobListResult:
    return service.list_product_jobs(product_id=product_id, limit=limit, cursor=cursor)


@router.get(
    "/products/{product_id}/sources/{source_id}/jobs",
    response_model=ProcessingJobListResult,
    status_code=http_status.HTTP_200_OK,
    summary="List source processing jobs",
    description="List one product source's jobs newest first with opaque pagination.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid processing-job cursor"},
        404: {"model": ErrorResponse, "description": "Parent product or source not found"},
        422: ERROR_422,
        503: ERROR_503,
    },
)
def list_source_processing_jobs(
    product_id: UUID,
    source_id: UUID,
    service: Annotated[ProcessingJobService, Depends(get_processing_job_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(min_length=1, max_length=4_096)] = None,
) -> ProcessingJobListResult:
    return service.list_source_jobs(
        product_id=product_id,
        source_id=source_id,
        limit=limit,
        cursor=cursor,
    )
