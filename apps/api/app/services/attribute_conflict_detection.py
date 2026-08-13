"""Product-level candidate agreement and conflict-detection orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeConflictCrossProductLineageError,
    AttributeConflictDetectionError,
    AttributeConflictNormalizationRequiredError,
    AttributeConflictRepositoryError,
    AttributeConflictResultStorageError,
    AttributeNormalizationRepositoryError,
    InvalidAttributeConflictDetectionJobError,
    ProcessingJobRepositoryError,
    ProductRepositoryError,
)
from app.domain.attribute_conflicts import AttributeConflictDetectionResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.attribute_conflicts import AttributeConflictDetectionResultRepository
from app.repositories.attribute_normalization import AttributeNormalizationResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.products import ProductRepository
from app.services.attribute_conflict_detection_engine import AttributeConflictDetectionEngine

logger = logging.getLogger(__name__)


class AttributeConflictDetectionService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        normalization_repository: AttributeNormalizationResultRepository,
        result_repository: AttributeConflictDetectionResultRepository,
        engine: AttributeConflictDetectionEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs = job_repository
        self._products = product_repository
        self._normalizations = normalization_repository
        self._results = result_repository
        self._engine = engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def detect_for_job(self, *, job_id: UUID) -> AttributeConflictDetectionResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.ATTRIBUTE_CONFLICT_DETECTION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.attribute_normalization_id is None
        ):
            raise InvalidAttributeConflictDetectionJobError()
        try:
            if self._products.get_by_id(job.product_id) is None:
                raise AttributeConflictNormalizationRequiredError()
            normalization = self._normalizations.get_by_id(job.attribute_normalization_id)
            if normalization is None:
                raise AttributeConflictNormalizationRequiredError()
            if normalization.product_id != job.product_id:
                raise AttributeConflictCrossProductLineageError()
            if any(
                candidate.source_extraction_id != normalization.extraction_id
                or candidate.classification_id != normalization.classification_id
                or candidate.category != normalization.category
                or candidate.schema_version != normalization.schema_version
                or candidate.schema_fingerprint != normalization.schema_fingerprint
                for candidate in normalization.candidates
            ):
                raise AttributeConflictNormalizationRequiredError()
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidAttributeConflictDetectionJobError()
        except AttributeConflictDetectionError:
            raise
        except (ProductRepositoryError, AttributeNormalizationRepositoryError) as exc:
            raise AttributeConflictNormalizationRequiredError() from exc
        except AttributeConflictRepositoryError as exc:
            raise AttributeConflictResultStorageError() from exc

        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        logger.info(
            "event=attribute_conflict_detection.started job_id=%s product_id=%s "
            "normalization_id=%s",
            job.job_id,
            job.product_id,
            normalization.normalization_id,
        )
        try:
            result = self._engine.detect(
                job_id=job.job_id,
                normalization_result=normalization,
                now=self._clock(),
            )
            stored = self._results.create(result)
        except AttributeConflictDetectionError as exc:
            self._fail(running, exc)
            raise
        except AttributeConflictRepositoryError as exc:
            error = AttributeConflictResultStorageError()
            self._fail(running, error)
            raise error from exc
        except Exception as exc:
            unexpected_error = AttributeConflictDetectionError()
            self._fail(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(
            running,
            result_reference=f"attribute-conflict-detection-results/{stored.conflict_detection_id}",
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=attribute_conflict_detection.completion_consistency_risk "
                "job_id=%s product_id=%s conflict_detection_id=%s",
                job.job_id,
                job.product_id,
                stored.conflict_detection_id,
            )
            raise
        logger.info(
            "event=attribute_conflict_detection.%s job_id=%s product_id=%s "
            "normalization_id=%s conflict_detection_id=%s attribute_count=%s "
            "conflict_count=%s indeterminate_count=%s engine=%s engine_version=%s",
            stored.status.value.lower(),
            job.job_id,
            job.product_id,
            normalization.normalization_id,
            stored.conflict_detection_id,
            stored.attribute_count,
            stored.conflict_count,
            stored.indeterminate_count,
            stored.engine,
            stored.engine_version,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: AttributeConflictDetectionError) -> None:
        failed = replace(running, error_code=error.code, error_message=error.safe_message)
        failed = transition_processing_job(failed, ProcessingJobStatus.FAILED, now=self._clock())
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=attribute_conflict_detection.completion_consistency_risk job_id=%s",
                running.job_id,
            )
