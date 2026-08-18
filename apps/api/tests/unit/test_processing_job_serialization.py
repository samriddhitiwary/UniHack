"""Processing-job DynamoDB mapping tests."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.exceptions import ProcessingJobSerializationError, ProductSerializationError
from app.domain.processing_jobs import ProcessingJob, ProcessingJobType
from app.utils.dynamodb import (
    deserialize_item,
    processing_job_from_item,
    processing_job_to_item,
    serialize_item,
    to_dynamodb_compatible,
)
from tests.fixtures.processing_jobs import JOB_CREATED_AT, make_processing_job
from tests.fixtures.products import PRODUCT_ID


def test_job_round_trip_preserves_uuid_enums_timestamps_and_optional_values() -> None:
    job = make_processing_job()
    mapped = processing_job_to_item(job)
    assert mapped["sourceScope"] == f"{job.product_id}#{job.source_id}"
    wire = serialize_item(mapped)
    assert processing_job_from_item(deserialize_item(wire)) == job
    assert wire["attempt"] == {"N": "1"}
    assert wire["startedAt"] == {"NULL": True}


def test_generic_serializer_still_rejects_python_float() -> None:
    with pytest.raises(ProductSerializationError):
        to_dynamodb_compatible({"progress": 1.5})


def test_catalog_export_projection_lineage_round_trips() -> None:
    projection_id = uuid4()
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.CATALOG_EXPORT,
        projection_id=projection_id,
        now=JOB_CREATED_AT,
    )
    item = processing_job_to_item(job)
    assert item["projectionId"] == projection_id
    assert processing_job_from_item(deserialize_item(serialize_item(item))) == job


@pytest.mark.parametrize(
    "mutation",
    [
        lambda item: item.pop("jobId"),
        lambda item: item.pop("productId"),
        lambda item: item.pop("sourceId"),
        lambda item: item.update(status="UNKNOWN"),
        lambda item: item.update(sourceScope="wrong#scope"),
        lambda item: item.update(attempt=Decimal("1.5")),
    ],
)
def test_malformed_job_item_raises_controlled_error(mutation: object) -> None:
    item = processing_job_to_item(make_processing_job())
    mutation(item)  # type: ignore[operator]
    with pytest.raises(ProcessingJobSerializationError):
        processing_job_from_item(item)
