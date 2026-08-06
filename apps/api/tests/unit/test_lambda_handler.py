"""Lambda entry-point foundation test."""

from mangum import Mangum

from app.lambda_handler import handler


def test_lambda_handler_wraps_fastapi_application() -> None:
    assert isinstance(handler, Mangum)
