"""Processing-job entity tests."""

from dataclasses import FrozenInstanceError
from datetime import UTC
from uuid import uuid4

import pytest

from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from tests.fixtures.processing_jobs import JOB_CREATED_AT, make_processing_job
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID


def test_create_job_uses_pending_defaults_uuid_and_utc() -> None:
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        job_type=ProcessingJobType.PDF_TEXT_EXTRACTION,
        now=JOB_CREATED_AT,
    )
    assert job.product_id == PRODUCT_ID and job.source_id == SOURCE_ID
    assert job.status is ProcessingJobStatus.PENDING
    assert job.attempt == 1 and job.progress_percent == 0 and job.version == 1
    assert job.created_at == job.updated_at == JOB_CREATED_AT
    assert job.created_at.tzinfo is UTC


def test_attribute_extraction_job_is_product_scoped_with_explicit_lineage() -> None:
    classification_id = uuid4()
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_EXTRACTION,
        classification_id=classification_id,
        now=JOB_CREATED_AT,
    )
    assert job.source_id is None and job.classification_id == classification_id


def test_attribute_extraction_job_requires_lineage_and_rejects_source_scope() -> None:
    with pytest.raises(ValueError):
        ProcessingJob.create(
            product_id=PRODUCT_ID, source_id=None, job_type=ProcessingJobType.ATTRIBUTE_EXTRACTION
        )


def test_attribute_normalization_job_is_product_scoped_with_explicit_extraction() -> None:
    extraction_id = uuid4()
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_NORMALIZATION,
        attribute_extraction_id=extraction_id,
        now=JOB_CREATED_AT,
    )
    assert job.source_id is None and job.attribute_extraction_id == extraction_id
    with pytest.raises(ValueError):
        ProcessingJob.create(
            product_id=PRODUCT_ID,
            source_id=None,
            job_type=ProcessingJobType.ATTRIBUTE_NORMALIZATION,
        )
    with pytest.raises(ValueError):
        ProcessingJob.create(
            product_id=PRODUCT_ID,
            source_id=SOURCE_ID,
            job_type=ProcessingJobType.ATTRIBUTE_EXTRACTION,
            classification_id=uuid4(),
        )


def test_job_is_immutable() -> None:
    with pytest.raises(FrozenInstanceError):
        make_processing_job().status = ProcessingJobStatus.RUNNING  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"attempt": 0},
        {"version": 0},
        {"progress_percent": -1},
        {"progress_percent": 101},
        {"status": "PENDING"},
        {"job_type": "SOURCE_PROCESSING"},
        {"result_reference": r"C:\\temp\\result"},
        {"result_reference": "../result"},
    ],
)
def test_job_rejects_invalid_values(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        make_processing_job(**changes)  # type: ignore[arg-type]


def test_optional_text_is_normalized() -> None:
    job = make_processing_job(error_code=" ", error_message=" ", result_reference=" ")
    assert job.error_code is None and job.error_message is None
    assert job.result_reference is None


def test_completed_requires_full_consistent_state() -> None:
    with pytest.raises(ValueError):
        make_processing_job(status=ProcessingJobStatus.COMPLETED, progress_percent=99)
