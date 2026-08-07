"""Global safe API exception mappings."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidProcessingJobCursorError,
    InvalidProductCursorError,
    InvalidProductSourceCursorError,
    InvalidProductSourceFileContentError,
    InvalidProductSourceFilenameError,
    InvalidProductSourceStatusTransitionError,
    ObjectSizeExceededError,
    ObjectStorageError,
    ProcessingJobAlreadyExistsError,
    ProcessingJobNotFoundError,
    ProcessingJobRepositoryError,
    ProcessingJobTypeNotSupportedForSourceError,
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceAlreadyExistsError,
    ProductSourceMimeTypeMismatchError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
    ProductSourceStorageConsistencyError,
    ProductSourceVersionConflictError,
    ProductVersionConflictError,
    UnsupportedProductSourceFileTypeError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(ProductNotFoundError, product_not_found_handler)
    application.add_exception_handler(ProductAlreadyExistsError, product_already_exists_handler)
    application.add_exception_handler(InvalidProductCursorError, invalid_product_cursor_handler)
    application.add_exception_handler(ProductVersionConflictError, product_version_conflict_handler)
    application.add_exception_handler(ProductRepositoryError, product_repository_handler)
    application.add_exception_handler(
        ProductSourceAlreadyExistsError, product_source_already_exists_handler
    )
    application.add_exception_handler(ProductSourceNotFoundError, product_source_not_found_handler)
    application.add_exception_handler(
        InvalidProductSourceCursorError, invalid_product_source_cursor_handler
    )
    application.add_exception_handler(
        ProductSourceVersionConflictError, product_source_version_conflict_handler
    )
    application.add_exception_handler(
        InvalidProductSourceStatusTransitionError,
        invalid_product_source_status_transition_handler,
    )
    application.add_exception_handler(
        ProductSourceStorageConsistencyError,
        product_source_storage_consistency_handler,
    )
    application.add_exception_handler(
        ProductSourceRepositoryError, product_source_repository_handler
    )
    application.add_exception_handler(
        InvalidProductSourceFilenameError, invalid_product_source_filename_handler
    )
    application.add_exception_handler(
        UnsupportedProductSourceFileTypeError, unsupported_product_source_file_type_handler
    )
    application.add_exception_handler(
        ProductSourceMimeTypeMismatchError, product_source_mime_type_mismatch_handler
    )
    application.add_exception_handler(
        InvalidProductSourceFileContentError, invalid_product_source_file_content_handler
    )
    application.add_exception_handler(ObjectSizeExceededError, object_size_exceeded_handler)
    application.add_exception_handler(ObjectStorageError, object_storage_handler)
    application.add_exception_handler(
        ProcessingJobAlreadyExistsError, processing_job_already_exists_handler
    )
    application.add_exception_handler(ProcessingJobNotFoundError, processing_job_not_found_handler)
    application.add_exception_handler(
        InvalidProcessingJobCursorError, invalid_processing_job_cursor_handler
    )
    application.add_exception_handler(
        ProcessingJobTypeNotSupportedForSourceError,
        processing_job_type_not_supported_handler,
    )
    application.add_exception_handler(
        ProcessingJobRepositoryError, processing_job_repository_handler
    )
    application.add_exception_handler(RequestValidationError, request_validation_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)


async def product_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    error = _expect_exception(exc, ProductNotFoundError)
    return _error_response(
        request,
        status_code=404,
        code="PRODUCT_NOT_FOUND",
        message="The requested product does not exist.",
        details={"productId": error.product_id},
    )


async def product_already_exists_handler(request: Request, exc: Exception) -> JSONResponse:
    error = _expect_exception(exc, ProductAlreadyExistsError)
    return _error_response(
        request,
        status_code=409,
        code="PRODUCT_ALREADY_EXISTS",
        message="A product with this identifier already exists.",
        details={"productId": error.product_id},
    )


async def invalid_product_cursor_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, InvalidProductCursorError)
    return _error_response(
        request,
        status_code=400,
        code="INVALID_PRODUCT_CURSOR",
        message="The product cursor is invalid.",
    )


async def product_version_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, ProductVersionConflictError)
    return _error_response(
        request,
        status_code=409,
        code="PRODUCT_VERSION_CONFLICT",
        message=(
            "The product was modified by another request. "
            "Retrieve the latest version and try again."
        ),
    )


async def product_repository_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "event=product.persistence_failed request_id=%s error_type=%s",
        _request_id(request),
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=503,
        code="PRODUCT_STORAGE_UNAVAILABLE",
        message="Product storage is temporarily unavailable.",
    )


async def product_source_already_exists_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, ProductSourceAlreadyExistsError)
    return _error_response(
        request,
        status_code=409,
        code="PRODUCT_SOURCE_ALREADY_EXISTS",
        message="A product source with this identifier already exists.",
    )


async def product_source_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    error = _expect_exception(exc, ProductSourceNotFoundError)
    details = {"productId": error.product_id}
    if error.source_id is not None:
        details["sourceId"] = error.source_id
    return _error_response(
        request,
        status_code=404,
        code="PRODUCT_SOURCE_NOT_FOUND",
        message="The requested product source does not exist.",
        details=details,
    )


async def invalid_product_source_cursor_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, InvalidProductSourceCursorError)
    return _error_response(
        request,
        status_code=400,
        code="INVALID_PRODUCT_SOURCE_CURSOR",
        message="The product source cursor is invalid.",
    )


async def product_source_version_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, ProductSourceVersionConflictError)
    return _error_response(
        request,
        status_code=409,
        code="PRODUCT_SOURCE_VERSION_CONFLICT",
        message=(
            "The product source was modified by another request. "
            "Retrieve the latest version and try again."
        ),
    )


async def invalid_product_source_status_transition_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    error = _expect_exception(exc, InvalidProductSourceStatusTransitionError)
    return _error_response(
        request,
        status_code=409,
        code="PRODUCT_SOURCE_STATUS_TRANSITION_INVALID",
        message="The requested product source status transition is not allowed.",
        details={
            "sourceId": error.source_id,
            "currentStatus": error.current_status,
            "requestedStatus": error.requested_status,
        },
    )


async def product_source_storage_consistency_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    error = _expect_exception(exc, ProductSourceStorageConsistencyError)
    logger.error(
        "event=product_source.storage_consistency_failed request_id=%s "
        "product_id=%s source_id=%s source_type=%s",
        _request_id(request),
        error.product_id,
        error.source_id,
        error.source_type,
    )
    return _error_response(
        request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
    )


async def product_source_repository_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "event=product_source.persistence_failed request_id=%s error_type=%s",
        _request_id(request),
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=503,
        code="PRODUCT_SOURCE_STORAGE_UNAVAILABLE",
        message="Product source storage is temporarily unavailable.",
    )


async def invalid_product_source_filename_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, InvalidProductSourceFilenameError)
    return _error_response(
        request,
        status_code=422,
        code="REQUEST_VALIDATION_FAILED",
        message="The upload filename is invalid.",
    )


async def unsupported_product_source_file_type_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    _expect_exception(exc, UnsupportedProductSourceFileTypeError)
    return _error_response(
        request,
        status_code=422,
        code="UNSUPPORTED_PRODUCT_SOURCE_FILE_TYPE",
        message="The product source file type is unsupported.",
    )


async def product_source_mime_type_mismatch_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    _expect_exception(exc, ProductSourceMimeTypeMismatchError)
    return _error_response(
        request,
        status_code=422,
        code="PRODUCT_SOURCE_MIME_TYPE_MISMATCH",
        message="The declared MIME type does not match the file type.",
    )


async def invalid_product_source_file_content_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    _expect_exception(exc, InvalidProductSourceFileContentError)
    return _error_response(
        request,
        status_code=422,
        code="INVALID_PRODUCT_SOURCE_FILE_CONTENT",
        message="The uploaded file content is invalid for its type.",
    )


async def object_size_exceeded_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, ObjectSizeExceededError)
    return _error_response(
        request,
        status_code=413,
        code="PRODUCT_SOURCE_FILE_TOO_LARGE",
        message="The product source file exceeds the permitted size.",
    )


async def object_storage_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "event=object_storage.request_failed request_id=%s error_type=%s",
        _request_id(request),
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=503,
        code="OBJECT_STORAGE_UNAVAILABLE",
        message="Object storage is temporarily unavailable.",
    )


async def processing_job_already_exists_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, ProcessingJobAlreadyExistsError)
    return _error_response(
        request,
        status_code=409,
        code="PROCESSING_JOB_ALREADY_EXISTS",
        message="A processing job with this identifier already exists.",
    )


async def processing_job_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    error = _expect_exception(exc, ProcessingJobNotFoundError)
    return _error_response(
        request,
        status_code=404,
        code="PROCESSING_JOB_NOT_FOUND",
        message="The requested processing job does not exist.",
        details={"jobId": error.job_id},
    )


async def invalid_processing_job_cursor_handler(request: Request, exc: Exception) -> JSONResponse:
    _expect_exception(exc, InvalidProcessingJobCursorError)
    return _error_response(
        request,
        status_code=400,
        code="INVALID_PROCESSING_JOB_CURSOR",
        message="The processing-job cursor is invalid.",
    )


async def processing_job_type_not_supported_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    error = _expect_exception(exc, ProcessingJobTypeNotSupportedForSourceError)
    return _error_response(
        request,
        status_code=422,
        code="PROCESSING_JOB_TYPE_NOT_SUPPORTED",
        message="The processing-job type is not supported for this source type.",
        details={"sourceType": error.source_type, "jobType": error.job_type},
    )


async def processing_job_repository_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "event=processing_job.persistence_failed request_id=%s error_type=%s",
        _request_id(request),
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=503,
        code="PROCESSING_JOB_STORAGE_UNAVAILABLE",
        message="Processing-job storage is temporarily unavailable.",
    )


async def request_validation_handler(request: Request, exc: Exception) -> JSONResponse:
    validation_error = _expect_exception(exc, RequestValidationError)
    issues = [
        {
            "field": ".".join(str(part) for part in issue["loc"]),
            "message": issue["msg"],
            "type": issue["type"],
        }
        for issue in validation_error.errors()
    ]
    return _error_response(
        request,
        status_code=422,
        code="REQUEST_VALIDATION_FAILED",
        message="The request contains invalid data.",
        details={"issues": issues},
    )


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "event=request.unexpected_failure request_id=%s error_type=%s",
        _request_id(request),
        type(exc).__name__,
    )
    return _error_response(
        request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
    )


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "details": details or {}},
            "requestId": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unavailable"))


def _expect_exception[T: Exception](exc: Exception, expected: type[T]) -> T:
    if not isinstance(exc, expected):
        raise TypeError(f"expected {expected.__name__}")
    return exc
