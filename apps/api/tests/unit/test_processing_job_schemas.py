"""Processing-job schema tests."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.processing_jobs import (
    ProcessingJobCreate,
    ProcessingJobListResult,
    ProcessingJobRecord,
    ProcessingJobUpdate,
)
from tests.fixtures.processing_jobs import make_processing_job
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID


def test_create_accepts_only_approved_fields_and_defaults_attempt() -> None:
    request = ProcessingJobCreate(
        productId=PRODUCT_ID, sourceId=SOURCE_ID, jobType="PDF_TEXT_EXTRACTION"
    )
    assert request.attempt == 1


@pytest.mark.parametrize(
    "field",
    [
        "jobId",
        "status",
        "progressPercent",
        "errorCode",
        "errorMessage",
        "resultReference",
        "createdAt",
        "startedAt",
        "completedAt",
        "updatedAt",
        "version",
        "unknown",
    ],
)
def test_create_rejects_system_and_unknown_fields(field: str) -> None:
    payload: dict[str, Any] = {
        "productId": str(PRODUCT_ID),
        "sourceId": str(SOURCE_ID),
        "jobType": "SOURCE_PROCESSING",
        field: 1,
    }
    with pytest.raises(ValidationError):
        ProcessingJobCreate.model_validate(payload)


@pytest.mark.parametrize("attempt", [0, -1, 1.0, "1", True])
def test_create_requires_positive_strict_attempt(attempt: object) -> None:
    with pytest.raises(ValidationError):
        ProcessingJobCreate.model_validate(
            {
                "productId": str(PRODUCT_ID),
                "sourceId": str(SOURCE_ID),
                "jobType": "SOURCE_PROCESSING",
                "attempt": attempt,
            }
        )


def test_update_accepts_mutable_fields_and_normalizes_blanks() -> None:
    update = ProcessingJobUpdate(
        version=1,
        status="RUNNING",
        progressPercent=25,
        errorCode=" ",
        errorMessage=None,
        resultReference=" processing-results/job ",
    )
    assert update.error_code is None and update.error_message is None
    assert update.result_reference == "processing-results/job"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"version": 1},
        {"version": 0, "status": "RUNNING"},
        {"version": 1, "status": None},
        {"version": 1, "progressPercent": None},
        {"version": 1, "progressPercent": -1},
        {"version": 1, "progressPercent": 101},
        {"version": 1, "resultReference": r"C:\\temp\\result"},
        {"version": 1, "jobId": "forbidden"},
        {"version": 1, "productId": str(PRODUCT_ID)},
        {"version": 1, "sourceId": str(SOURCE_ID)},
        {"version": 1, "jobType": "CSV_PROCESSING"},
        {"version": 1, "attempt": 2},
        {"version": 1, "createdAt": "2026-08-07T00:00:00Z"},
        {"version": 1, "unknown": "x"},
    ],
)
def test_update_rejects_invalid_empty_and_immutable_fields(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProcessingJobUpdate.model_validate(payload)


def test_record_and_list_use_camel_case() -> None:
    record = ProcessingJobRecord.model_validate(make_processing_job())
    result = ProcessingJobListResult(items=[record], nextCursor="opaque")
    body = result.model_dump(by_alias=True, mode="json")
    assert body["items"][0]["jobId"]
    assert body["items"][0]["progressPercent"] == 0
    assert body["nextCursor"] == "opaque"
