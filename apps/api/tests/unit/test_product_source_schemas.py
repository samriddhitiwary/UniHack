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
        version=3,
        status=ProductSourceStatus.FAILED,
        displayName=None,
        errorMessage=" safe failure ",
    )
    assert update.model_fields_set == {"version", "status", "display_name", "error_message"}
    assert update.display_name is None
    assert update.error_message == "safe failure"


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1, "displayName": "Updated"},
        {"version": 1, "status": "PROCESSING"},
        {"version": 1, "errorMessage": "Safe failure"},
        {
            "version": 2,
            "displayName": "Updated",
            "status": "FAILED",
            "errorMessage": "Safe failure",
        },
    ],
)
def test_update_accepts_approved_partial_requests(payload: dict[str, Any]) -> None:
    update = ProductSourceUpdate.model_validate(payload)
    assert update.version >= 1


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"version": 1},
        {"version": 1, "status": None},
        {"version": 0, "displayName": "x"},
        {"version": -1, "displayName": "x"},
        {"version": 1.0, "displayName": "x"},
        {"version": "1", "displayName": "x"},
        {"version": True, "displayName": "x"},
        {"errorMessage": "x" * 2_001},
    ],
)
def test_update_rejects_missing_invalid_version_or_invalid_values(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        ProductSourceUpdate.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "sourceId",
        "productId",
        "sourceType",
        "originalFilename",
        "storageKey",
        "mimeType",
        "fileSizeBytes",
        "checksumSha256",
        "textContent",
        "createdAt",
        "updatedAt",
        "unknown",
    ],
)
def test_update_rejects_immutable_and_unknown_fields(field: str) -> None:
    payload: dict[str, Any] = {"version": 1, "displayName": "valid", field: "forbidden"}
    with pytest.raises(ValidationError):
        ProductSourceUpdate.model_validate(payload)


def test_update_distinguishes_omitted_explicit_null_and_blank() -> None:
    omitted = ProductSourceUpdate(version=1, status=ProductSourceStatus.READY)
    assert omitted.model_fields_set == {"version", "status"}

    cleared = ProductSourceUpdate(version=1, displayName=None, errorMessage=None)
    assert cleared.display_name is None
    assert cleared.error_message is None
    assert cleared.model_fields_set == {"version", "display_name", "error_message"}

    blank = ProductSourceUpdate(version=1, displayName="   ", errorMessage="   ")
    assert blank.display_name is None
    assert blank.error_message is None


def test_record_and_list_models_use_public_camel_case_shape() -> None:
    record = ProductSourceRecord.model_validate(make_product_source())
    result = ProductSourceListResult(items=[record], nextCursor="opaque")
    body = result.model_dump(by_alias=True, mode="json")
    assert body["items"][0]["sourceId"]
    assert body["items"][0]["sourceType"] == "PDF"
    assert body["nextCursor"] == "opaque"
