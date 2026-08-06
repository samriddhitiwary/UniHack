"""Product-source Pydantic schema tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.product_sources import ProductSourceStatus, ProductSourceType
from app.schemas.product_sources import (
    ProductSourceCreate,
    ProductSourceListResult,
    ProductSourceRecord,
    ProductSourceUpdate,
)
from tests.fixtures.product_sources import make_product_source
from tests.fixtures.products import PRODUCT_ID


def test_create_accepts_caller_fields_and_normalizes_values() -> None:
    request = ProductSourceCreate(
        productId=PRODUCT_ID,
        sourceType=ProductSourceType.PDF,
        originalFilename="  data.pdf  ",
        mimeType="APPLICATION/PDF",
        checksumSha256="A" * 64,
    )
    assert request.original_filename == "data.pdf"
    assert request.mime_type == "application/pdf"
    assert request.checksum_sha256 == "a" * 64


@pytest.mark.parametrize(
    "field",
    ["sourceId", "status", "errorMessage", "createdAt", "updatedAt", "version"],
)
def test_create_rejects_system_fields(field: str) -> None:
    payload: dict[str, Any] = {
        "productId": str(PRODUCT_ID),
        "sourceType": "PDF",
        "originalFilename": "data.pdf",
        field: "forbidden",
    }
    with pytest.raises(ValidationError):
        ProductSourceCreate.model_validate(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"productId": str(PRODUCT_ID), "sourceType": "PDF"},
        {
            "productId": str(PRODUCT_ID),
            "sourceType": "IMAGE",
            "originalFilename": "image.png",
            "mimeType": "application/pdf",
        },
        {
            "productId": str(PRODUCT_ID),
            "sourceType": "CSV",
            "originalFilename": "data.csv",
            "textContent": "a,b",
        },
        {
            "productId": str(PRODUCT_ID),
            "sourceType": "TEXT",
            "textContent": "x" * 50_001,
        },
        {
            "productId": str(PRODUCT_ID),
            "sourceType": "PDF",
            "originalFilename": "data.pdf",
            "checksumSha256": "bad",
        },
    ],
)
def test_create_enforces_cross_field_and_length_rules(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ProductSourceCreate.model_validate(payload)


def test_update_tracks_explicit_null_and_allows_only_mutable_fields() -> None:
    update = ProductSourceUpdate(
        status=ProductSourceStatus.FAILED,
        storageKey=None,
        errorMessage=" safe failure ",
    )
    assert update.model_fields_set == {"status", "storage_key", "error_message"}
    assert update.storage_key is None
    assert update.error_message == "safe failure"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": None},
        {"sourceId": "forbidden"},
        {"productId": str(PRODUCT_ID)},
        {"sourceType": "TEXT"},
        {"originalFilename": "forbidden.txt"},
        {"createdAt": "2026-08-06T12:00:00Z"},
        {"version": 1},
        {"errorMessage": "x" * 2_001},
        {"checksumSha256": "z" * 64},
        {"storageKey": "C:\\absolute\\source.pdf"},
        {"unknown": "value"},
    ],
)
def test_update_rejects_empty_immutable_invalid_or_extra_fields(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ProductSourceUpdate.model_validate(payload)


def test_record_and_list_models_use_public_camel_case_shape() -> None:
    record = ProductSourceRecord.model_validate(make_product_source())
    result = ProductSourceListResult(items=[record], nextCursor="opaque")
    body = result.model_dump(by_alias=True, mode="json")
    assert body["items"][0]["sourceId"]
    assert body["items"][0]["sourceType"] == "PDF"
    assert body["nextCursor"] == "opaque"
