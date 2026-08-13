from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeConflictCandidateLimitExceededError,
    AttributeConflictCrossProductLineageError,
    AttributeConflictNormalizationRequiredError,
)
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.services.attribute_conflict_detection import AttributeConflictDetectionService
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine
from app.services.attribute_normalization_engine import AttributeNormalizationEngine
from tests.fixtures.attribute_normalization import NOW, PRODUCT_ID, candidate, extraction


class Jobs:
    def __init__(self, job):
        self.job, self.updates = job, []

    def get_by_id(self, job_id):
        return self.job if self.job.job_id == job_id else None

    def update(self, job, expected_version):
        self.updates.append(job)
        self.job = replace(
            job,
            version=expected_version + 1,
            updated_at=NOW + timedelta(seconds=len(self.updates)),
        )
        return self.job


class Results:
    def __init__(self):
        self.value = None

    def get_by_job_id(self, job_id):
        return self.value

    def create(self, value):
        self.value = value
        return value


def fixture(*, product_exists=True, normalization_exists=True, cross_product=False, limit=100):
    schema = induction_motor_schema_v1()
    extracted = extraction(
        schema,
        (
            candidate(schema, "voltage", "415", "V", index=1),
            candidate(schema, "voltage", "440", "V", index=2),
        ),
    )
    normalization = AttributeNormalizationEngine().normalize(
        job_id=uuid4(), extraction_result=extracted, schema=schema, now=NOW
    )
    if cross_product:
        normalization = replace(normalization, product_id=uuid4())
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_CONFLICT_DETECTION,
        attribute_normalization_id=normalization.normalization_id,
        now=NOW,
    )
    jobs, results = Jobs(job), Results()
    service = AttributeConflictDetectionService(
        job_repository=jobs,
        product_repository=SimpleNamespace(
            get_by_id=lambda _: object() if product_exists else None
        ),
        normalization_repository=SimpleNamespace(
            get_by_id=lambda _: normalization if normalization_exists else None
        ),
        result_repository=results,
        engine=AttributeConflictDetectionEngine(max_candidates_per_attribute=limit),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, results


def test_result_is_persisted_before_job_completion() -> None:
    service, jobs, results = fixture()
    result = service.detect_for_job(job_id=jobs.job.job_id)
    assert results.value is result and result.conflict_count == 1
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.result_reference.endswith(str(result.conflict_detection_id))


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"product_exists": False}, AttributeConflictNormalizationRequiredError),
        ({"normalization_exists": False}, AttributeConflictNormalizationRequiredError),
        ({"cross_product": True}, AttributeConflictCrossProductLineageError),
    ],
)
def test_prerequisite_failures_do_not_start_the_job(kwargs, error) -> None:
    service, jobs, _ = fixture(**kwargs)
    with pytest.raises(error):
        service.detect_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_technical_failure_after_start_marks_job_failed() -> None:
    service, jobs, _ = fixture(limit=1)
    with pytest.raises(AttributeConflictCandidateLimitExceededError):
        service.detect_for_job(job_id=jobs.job.job_id)
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.FAILED,
    ]
    assert jobs.job.error_code == "ATTRIBUTE_CONFLICT_CANDIDATE_LIMIT_EXCEEDED"
