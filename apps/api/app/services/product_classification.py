"""Internal orchestration of a product-level classification job."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    InvalidProductClassificationJobError,
    ProcessingJobRepositoryError,
    ProductClassificationError,
    ProductClassificationProductNotFoundError,
    ProductClassificationRepositoryError,
    ProductClassificationResultStorageError,
    ProductRepositoryError,
)
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_classification import ProductClassificationResult
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_classification import ProductClassificationResultRepository
from app.repositories.products import ProductRepository
from app.services.product_classification_engine import ProductClassificationEngine
from app.services.product_classification_evidence import ProductClassificationEvidenceAggregator

logger = logging.getLogger(__name__)


class ProductClassificationService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        result_repository: ProductClassificationResultRepository,
        evidence_aggregator: ProductClassificationEvidenceAggregator,
        engine: ProductClassificationEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs = job_repository
        self._products = product_repository
        self._results = result_repository
        self._evidence = evidence_aggregator
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def classify_for_job(self, *, job_id: UUID) -> ProductClassificationResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.PRODUCT_CLASSIFICATION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
        ):
            raise InvalidProductClassificationJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise ProductClassificationProductNotFoundError()
        except ProductRepositoryError as exc:
            raise ProductClassificationError() from exc
        try:
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidProductClassificationJobError()
        except ProductClassificationRepositoryError as exc:
            raise ProductClassificationResultStorageError() from exc
        running = self._start(job)
        logger.info(
            "event=product_classification.started job_id=%s product_id=%s",
            job.job_id,
            job.product_id,
        )
        try:
            evidence = self._evidence.collect(job.product_id)
            logger.info(
                "event=product_classification.evidence_collected job_id=%s "
                "product_id=%s evidence_count=%s source_count=%s",
                job.job_id,
                job.product_id,
                len(evidence),
                len({item.source_id for item in evidence}),
            )
            decision = self._engine.classify(evidence)
            result = ProductClassificationResult.create(
                job_id=job.job_id,
                product_id=job.product_id,
                decision=decision,
                evidence_item_count=len(evidence),
                now=self._clock(),
            )
            stored = self._results.create(result)
        except ProductClassificationError as exc:
            self._fail(running, exc)
            raise
        except ProductClassificationRepositoryError as exc:
            storage_error = ProductClassificationResultStorageError()
            self._fail(running, storage_error)
            raise storage_error from exc
        except Exception as exc:
            unexpected_error = ProductClassificationError()
            self._fail(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(
            running, result_reference=f"product-classification-results/{stored.classification_id}"
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=product_classification.completion_consistency_risk job_id=%s "
                "product_id=%s classification_id=%s",
                job.job_id,
                job.product_id,
                stored.classification_id,
            )
            raise
        logger.info(
            "event=product_classification.%s job_id=%s product_id=%s category=%s "
            "confidence_bp=%s pump_score=%s motor_score=%s evidence_count=%s match_count=%s "
            "engine=%s engine_version=%s",
            stored.status.value.lower(),
            job.job_id,
            job.product_id,
            stored.category.value,
            stored.confidence_bp,
            stored.pump_score,
            stored.motor_score,
            stored.evidence_item_count,
            len(stored.matches),
            stored.engine,
            stored.engine_version,
        )
        return stored

    def _start(self, job: ProcessingJob) -> ProcessingJob:
        candidate = transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock())
        return self._jobs.update(candidate, expected_version=job.version)

    def _fail(self, running: ProcessingJob, error: ProductClassificationError) -> None:
        failed = replace(running, error_code=error.code, error_message=error.safe_message)
        failed = transition_processing_job(failed, ProcessingJobStatus.FAILED, now=self._clock())
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=product_classification.completion_consistency_risk job_id=%s product_id=%s",
                running.job_id,
                running.product_id,
            )
