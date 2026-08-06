"""Global safe API exception mappings."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    InvalidProductCursorError,
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductRepositoryError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(ProductNotFoundError, product_not_found_handler)
    application.add_exception_handler(ProductAlreadyExistsError, product_already_exists_handler)
    application.add_exception_handler(InvalidProductCursorError, invalid_product_cursor_handler)
    application.add_exception_handler(ProductRepositoryError, product_repository_handler)
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
