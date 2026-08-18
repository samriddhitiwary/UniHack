from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.core.exceptions import (
    ProcessingJobRepositoryError,
    ReviewedAttributeRepositoryError,
    ReviewedMaterializationAlreadyExistsError,
    ReviewedMaterializationResultStorageError,
    ReviewedMaterializationReviewNotCompletedError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_review import ProductReviewSessionStatus, ReviewDecisionPage
from app.services.review_decision_resolver import ReviewDecisionResolver
from app.services.reviewed_attribute_materialization import (
    ReviewedAttributeMaterializationService,
)
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)
from app.utils.dynamodb import (
    deserialize_item,
    processing_job_from_item,
    processing_job_to_item,
    serialize_item,
)
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.reviewed_attributes import completed_review


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
    value = None

    def get_by_review_id(self, review_id):
        return self.value

    def create(self, value):
        self.value = value
        return value


def setup_service(*, results=None, jobs_class=Jobs, open_review=False):
    schema, normalization, _, validation, _, selection, review, decisions, current = (
        completed_review()
    )
    if open_review:
        review = replace(review, status=ProductReviewSessionStatus.OPEN, completed_at=None)
    job = ProcessingJob.create(
        product_id=review.product_id,
        source_id=None,
        review_id=review.review_id,
        job_type=ProcessingJobType.REVIEWED_ATTRIBUTE_MATERIALIZATION,
        now=NOW,
    )
    jobs, stored = jobs_class(job), results or Results()
    reviews = SimpleNamespace(
        get_by_id=lambda _: review,
        list_current_decisions=lambda _: current,
        list_decisions=lambda _review_id, limit, cursor=None: ReviewDecisionPage(decisions, None),
    )
    service = ReviewedAttributeMaterializationService(
        job_repository=jobs,
        product_repository=SimpleNamespace(get_by_id=lambda _: object()),
        review_repository=reviews,
        selection_repository=SimpleNamespace(get_by_id=lambda _: selection),
        validation_repository=SimpleNamespace(get_by_id=lambda _: validation),
        normalization_repository=SimpleNamespace(get_by_id=lambda _: normalization),
        schema_repository=SimpleNamespace(get_by_category_and_version=lambda *_: schema),
        result_repository=stored,
        resolver=ReviewDecisionResolver(),
        engine=ReviewedAttributeMaterializationEngine(),
        clock=lambda: NOW + timedelta(seconds=10),
    )
    return service, jobs, stored, review


def test_persists_before_completion_and_sets_result_reference() -> None:
    service, jobs, results, _ = setup_service()
    result = service.materialize_for_job(job_id=jobs.job.job_id)
    assert results.value is result
    assert [item.status for item in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    assert jobs.job.result_reference == f"reviewed-attribute-results/{result.materialization_id}"


def test_materialization_job_review_lineage_round_trips() -> None:
    _, jobs, _, review = setup_service()
    item = processing_job_to_item(jobs.job)
    assert item["reviewId"] == review.review_id
    assert processing_job_from_item(deserialize_item(serialize_item(item))) == jobs.job


def test_open_review_and_duplicate_do_not_start_job() -> None:
    service, jobs, _, _ = setup_service(open_review=True)
    with pytest.raises(ReviewedMaterializationReviewNotCompletedError):
        service.materialize_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []

    existing = Results()
    existing.value = object()
    service, jobs, _, _ = setup_service(results=existing)
    with pytest.raises(ReviewedMaterializationAlreadyExistsError):
        service.materialize_for_job(job_id=jobs.job.job_id)
    assert jobs.updates == []


def test_persistence_failure_marks_running_job_failed() -> None:
    class FailingResults(Results):
        def create(self, value):
            raise ReviewedAttributeRepositoryError()

    service, jobs, _, _ = setup_service(results=FailingResults())
    with pytest.raises(ReviewedMaterializationResultStorageError):
        service.materialize_for_job(job_id=jobs.job.job_id)
    assert jobs.updates[-1].status is ProcessingJobStatus.FAILED


def test_completion_failure_preserves_artifact_and_logs_risk(caplog) -> None:
    class CompletionFailingJobs(Jobs):
        def update(self, job, expected_version):
            if self.updates:
                raise ProcessingJobRepositoryError()
            return super().update(job, expected_version)

    service, jobs, results, _ = setup_service(jobs_class=CompletionFailingJobs)
    with pytest.raises(ProcessingJobRepositoryError):
        service.materialize_for_job(job_id=jobs.job.job_id)
    assert results.value is not None and jobs.job.status is ProcessingJobStatus.RUNNING
    assert "reviewed_attribute_materialization.completion_consistency_risk" in caplog.text
