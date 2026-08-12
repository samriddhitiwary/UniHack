"""Orchestrate one bounded image-analysis job."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    ImageAnalysisError,
    ImageAnalysisRepositoryError,
    ImageAnalysisResultStorageError,
    ImageObjectNotFoundError,
    ImageObjectStorageError,
    InvalidImageAnalysisJobError,
    InvalidImageSourceError,
    ObjectNotFoundError,
    ObjectStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.image_analysis import ImageAnalysisResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSourceType
from app.repositories.image_analysis import ImageAnalysisResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services.image_inspector import (
    PARSER_NAME,
    PARSER_VERSION,
    SUPPORTED_MIME_FORMATS,
    ImageInspector,
)
from app.storage.protocol import ObjectStorage

logger = logging.getLogger(__name__)


class ImageAnalysisService:
    """Analyze image metadata through protocols; no OCR, worker, or API."""

    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        source_repository: ProductSourceRepository,
        object_storage: ObjectStorage,
        result_repository: ImageAnalysisResultRepository,
        inspector: ImageInspector,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._source_repository = source_repository
        self._object_storage = object_storage
        self._result_repository = result_repository
        self._inspector = inspector
        self._clock = clock or (lambda: datetime.now(UTC))

    def analyze_for_job(self, *, job_id: UUID) -> ImageAnalysisResult:
        job = self._job_repository.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.IMAGE_ANALYSIS
            or job.status is not ProcessingJobStatus.PENDING
        ):
            raise InvalidImageAnalysisJobError()
        source = self._source_repository.get_by_id(job.product_id, job.source_id)
        if (
            source is None
            or source.source_type is not ProductSourceType.IMAGE
            or source.storage_key is None
            or source.mime_type not in SUPPORTED_MIME_FORMATS
        ):
            raise InvalidImageSourceError()
        if self._result_repository.get_by_job_id(job.job_id) is not None:
            raise InvalidImageAnalysisJobError()

        logger.info(
            "event=image_analysis.started job_id=%s product_id=%s source_id=%s",
            job.job_id,
            job.product_id,
            job.source_id,
        )
        running = self._start_job(job)
        try:
            with self._object_storage.open(source.storage_key) as stream:
                logger.info(
                    "event=image_analysis.image_opened job_id=%s product_id=%s source_id=%s",
                    job.job_id,
                    job.product_id,
                    job.source_id,
                )
                inspected = self._inspector.inspect(
                    stream,
                    expected_mime_type=source.mime_type,
                    expected_size_bytes=source.file_size_bytes,
                )
            logger.info(
                "event=image_analysis.metadata_extracted job_id=%s product_id=%s "
                "source_id=%s format=%s width=%s height=%s pixel_count=%s color_mode=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                inspected.metadata.format,
                inspected.metadata.width,
                inspected.metadata.height,
                inspected.metadata.pixel_count,
                inspected.metadata.color_mode,
            )
            logger.info(
                "event=image_analysis.regions_generated job_id=%s product_id=%s "
                "source_id=%s region_count=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                len(inspected.regions),
            )
            result = ImageAnalysisResult.create(
                job_id=job.job_id,
                product_id=job.product_id,
                source_id=job.source_id,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
                metadata=inspected.metadata,
                regions=inspected.regions,
                now=self._clock(),
            )
            stored = self._result_repository.create(result)
        except ObjectNotFoundError as exc:
            error = ImageObjectNotFoundError()
            self._fail_job(running, error)
            raise error from exc
        except ObjectStorageError as exc:
            storage_error = ImageObjectStorageError()
            self._fail_job(running, storage_error)
            raise storage_error from exc
        except ImageAnalysisError as exc:
            self._fail_job(running, exc)
            raise
        except ImageAnalysisRepositoryError:
            result_error = ImageAnalysisResultStorageError()
            self._fail_job(running, result_error)
            raise
        except Exception as exc:
            unexpected_error = ImageAnalysisError()
            self._fail_job(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(
            running, result_reference=f"image-analysis-results/{stored.analysis_id}"
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._job_repository.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=image_analysis.completion_consistency_risk job_id=%s product_id=%s "
                "source_id=%s analysis_id=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                stored.analysis_id,
            )
            raise
        logger.info(
            "event=image_analysis.completed job_id=%s product_id=%s source_id=%s format=%s "
            "width=%s height=%s pixel_count=%s color_mode=%s region_count=%s "
            "candidate_status=%s heuristic_score=%s",
            job.job_id,
            job.product_id,
            job.source_id,
            stored.metadata.format,
            stored.metadata.width,
            stored.metadata.height,
            stored.metadata.pixel_count,
            stored.metadata.color_mode,
            len(stored.regions),
            stored.nameplate_candidate_status.value,
            stored.heuristic_score,
        )
        return stored

    def _start_job(self, job: ProcessingJob) -> ProcessingJob:
        candidate = transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock())
        return self._job_repository.update(candidate, expected_version=job.version)

    def _fail_job(self, running: ProcessingJob, error: ImageAnalysisError) -> None:
        candidate = replace(running, error_code=error.code, error_message=error.safe_message)
        candidate = transition_processing_job(
            candidate, ProcessingJobStatus.FAILED, now=self._clock()
        )
        try:
            self._job_repository.update(candidate, expected_version=running.version)
        except ProcessingJobRepositoryError as update_error:
            logger.error(
                "event=image_analysis.failure_state_update_failed job_id=%s product_id=%s "
                "source_id=%s error_code=%s error_type=%s",
                running.job_id,
                running.product_id,
                running.source_id,
                error.code,
                type(update_error).__name__,
            )
        logger.warning(
            "event=image_analysis.failed job_id=%s product_id=%s source_id=%s error_code=%s",
            running.job_id,
            running.product_id,
            running.source_id,
            error.code,
        )
