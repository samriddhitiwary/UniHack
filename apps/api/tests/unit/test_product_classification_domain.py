"""Product-level job and classification-result invariant tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.processing_jobs import ProcessingJob, ProcessingJobType
from app.domain.product_classification import ProductClassificationResult
from app.services.product_classification_engine import ProductClassificationEngine
from app.utils.dynamodb import (
    deserialize_item,
    processing_job_from_item,
    processing_job_to_item,
    serialize_item,
)


def test_product_classification_job_is_product_scoped() -> None:
    job = ProcessingJob.create(
        product_id=uuid4(),
        source_id=None,
        job_type=ProcessingJobType.PRODUCT_CLASSIFICATION,
    )
    assert job.source_id is None
    item = processing_job_to_item(job)
    assert "sourceId" not in item and "sourceScope" not in item
    assert processing_job_from_item(deserialize_item(serialize_item(item))) == job


def test_source_jobs_still_require_source_and_classification_rejects_one() -> None:
    with pytest.raises(ValueError):
        ProcessingJob.create(
            product_id=uuid4(),
            source_id=None,
            job_type=ProcessingJobType.CSV_PROCESSING,
        )
    with pytest.raises(ValueError):
        ProcessingJob.create(
            product_id=uuid4(),
            source_id=uuid4(),
            job_type=ProcessingJobType.PRODUCT_CLASSIFICATION,
        )


def test_result_captures_engine_identity_and_counts() -> None:
    evidence = ()
    decision = ProductClassificationEngine().classify(evidence)
    result = ProductClassificationResult.create(
        job_id=uuid4(),
        product_id=uuid4(),
        decision=decision,
        evidence_item_count=0,
        now=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert result.engine == "deterministic-rule-v1"
    assert result.engine_version == "1.0"
    assert result.evidence_item_count == 0
