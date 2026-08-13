from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeNormalizationCandidateLimitExceededError,
    AttributeNormalizationExtractionRequiredError,
    AttributeNormalizationSchemaMismatchError,
)
from app.domain.category_schemas.builtins import induction_motor_schema_v1
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.services.attribute_normalization import AttributeNormalizationService
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


def fixture(
    *,
    product_exists=True,
    extraction_exists=True,
    cross_product=False,
    schema_mismatch=False,
    max_candidates=5_000,
):
    schema = induction_motor_schema_v1()
    source = candidate(schema, "ratedPower", "5500", "W")
    sources = (
        (source, candidate(schema, "voltage", "415", "V", index=2))
        if max_candidates == 1
        else (source,)
    )
    extracted = extraction(schema, sources)
    if cross_product:
        extracted = replace(extracted, product_id=uuid4())
    if schema_mismatch:
        extracted = replace(extracted, schema_fingerprint="f" * 64)
    job = ProcessingJob.create(
        product_id=PRODUCT_ID,
        source_id=None,
        job_type=ProcessingJobType.ATTRIBUTE_NORMALIZATION,
        attribute_extraction_id=extracted.extraction_id,
        now=NOW,
    )
    jobs, results = Jobs(job), Results()
    service = AttributeNormalizationService(
        job_repository=jobs,
        product_repository=SimpleNamespace(
            get_by_id=lambda _: object() if product_exists else None
        ),
        extraction_repository=SimpleNamespace(
            get_by_id=lambda _: extracted if extraction_exists else None
        ),
        schema_repository=SimpleNamespace(get_by_category_and_version=lambda *_: schema),
        result_repository=results,
        engine=AttributeNormalizationEngine(max_candidates=max_candidates),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, results, extracted


def test_conversion_result_persists_before_successful_completion() -> None:
    service, jobs, results, extracted = fixture()
    result = service.normalize_for_job(job_id=jobs.job.job_id)
    assert results.value is result and result.extraction_id == extracted.extraction_id
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.progress_percent == 100
    assert jobs.job.result_reference.endswith(str(result.normalization_id))


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"product_exists": False}, AttributeNormalizationExtractionRequiredError),
        ({"extraction_exists": False}, AttributeNormalizationExtractionRequiredError),
        ({"cross_product": True}, AttributeNormalizationExtractionRequiredError),
        ({"schema_mismatch": True}, AttributeNormalizationSchemaMismatchError),
    ],
)
def test_invalid_lineage_is_rejected_before_running(kwargs, error) -> None:
    service, jobs, _, _ = fixture(**kwargs)
    with pytest.raises(error):
        service.normalize_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_post_start_candidate_limit_marks_job_failed() -> None:
    service, jobs, _, _ = fixture(max_candidates=1)
    with pytest.raises(AttributeNormalizationCandidateLimitExceededError):
        service.normalize_for_job(job_id=jobs.job.job_id)
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.FAILED,
    ]
    assert jobs.job.error_code == "ATTRIBUTE_NORMALIZATION_CANDIDATE_LIMIT_EXCEEDED"
