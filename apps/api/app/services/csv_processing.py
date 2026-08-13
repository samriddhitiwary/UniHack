"""Orchestrate one bounded CSV processing job."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    CsvObjectNotFoundError,
    CsvObjectStorageError,
    CsvProcessingError,
    CsvProcessingRepositoryError,
    CsvProcessingResultStorageError,
    InvalidCsvProcessingJobError,
    InvalidCsvSourceError,
    ObjectNotFoundError,
    ObjectStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.csv_processing import CsvProcessingQualityStatus, CsvProcessingResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSourceType
from app.repositories.csv_processing import CsvProcessingResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services.csv_parser import CsvParser
from app.storage.protocol import ObjectStorage

logger = logging.getLogger(__name__)


class CsvProcessingService:
    """Process CSV through repository and storage protocols; no worker or API."""

    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        source_repository: ProductSourceRepository,
        object_storage: ObjectStorage,
        result_repository: CsvProcessingResultRepository,
        parser: CsvParser,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._source_repository = source_repository
        self._object_storage = object_storage
        self._result_repository = result_repository
        self._parser = parser
        self._clock = clock or (lambda: datetime.now(UTC))

    def process_for_job(self, *, job_id: UUID) -> CsvProcessingResult:
        job = self._job_repository.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.CSV_PROCESSING
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is None
        ):
            raise InvalidCsvProcessingJobError()
        source = self._source_repository.get_by_id(job.product_id, job.source_id)
        if (
            source is None
            or source.source_type is not ProductSourceType.CSV
            or source.storage_key is None
        ):
            raise InvalidCsvSourceError()
        if self._result_repository.get_by_job_id(job.job_id) is not None:
            raise InvalidCsvProcessingJobError()

        logger.info(
            "event=csv_processing.started job_id=%s product_id=%s source_id=%s",
            job.job_id,
            job.product_id,
            job.source_id,
        )
        running = self._start_job(job)
        try:
            with self._object_storage.open(source.storage_key) as stream:
                logger.info(
                    "event=csv_processing.csv_opened job_id=%s product_id=%s source_id=%s",
                    job.job_id,
                    job.product_id,
                    job.source_id,
                )
                parsed = self._parser.parse(stream)
            logger.info(
                "event=csv_processing.dialect_detected job_id=%s encoding=%s delimiter=%r",
                job.job_id,
                parsed.encoding,
                parsed.delimiter,
            )
            result = CsvProcessingResult.create(
                job_id=job.job_id,
                product_id=job.product_id,
                source_id=job.source_id,
                encoding=parsed.encoding,
                delimiter=parsed.delimiter,
                header=parsed.header,
                rows=parsed.rows,
                now=self._clock(),
            )
            stored = self._result_repository.create(result)
        except ObjectNotFoundError as exc:
            error = CsvObjectNotFoundError()
            self._fail_job(running, error)
            raise error from exc
        except ObjectStorageError as exc:
            storage_error = CsvObjectStorageError()
            self._fail_job(running, storage_error)
            raise storage_error from exc
        except CsvProcessingError as exc:
            self._fail_job(running, exc)
            raise
        except CsvProcessingRepositoryError:
            result_error = CsvProcessingResultStorageError()
            self._fail_job(running, result_error)
            raise
        except Exception as exc:
            unexpected_error = CsvProcessingError()
            self._fail_job(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(
            running, result_reference=f"csv-processing-results/{stored.processing_id}"
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._job_repository.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=csv_processing.completion_consistency_risk job_id=%s product_id=%s "
                "source_id=%s processing_id=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                stored.processing_id,
            )
            raise

        event = (
            "csv_processing.completed_with_warnings"
            if stored.quality_status is CsvProcessingQualityStatus.VALID_WITH_WARNINGS
            else "csv_processing.completed"
        )
        logger.info(
            "event=%s job_id=%s product_id=%s source_id=%s encoding=%s delimiter=%r "
            "column_count=%s row_count=%s malformed_row_count=%s total_cells=%s quality_status=%s",
            event,
            job.job_id,
            job.product_id,
            job.source_id,
            stored.encoding,
            stored.delimiter,
            stored.column_count,
            stored.row_count,
            stored.malformed_row_count,
            stored.total_cell_count,
            stored.quality_status.value,
        )
        return stored

    def _start_job(self, job: ProcessingJob) -> ProcessingJob:
        candidate = transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock())
        return self._job_repository.update(candidate, expected_version=job.version)

    def _fail_job(self, running: ProcessingJob, error: CsvProcessingError) -> None:
        candidate = replace(running, error_code=error.code, error_message=error.safe_message)
        candidate = transition_processing_job(
            candidate, ProcessingJobStatus.FAILED, now=self._clock()
        )
        try:
            self._job_repository.update(candidate, expected_version=running.version)
        except ProcessingJobRepositoryError as update_error:
            logger.error(
                "event=csv_processing.failure_state_update_failed job_id=%s product_id=%s "
                "source_id=%s error_code=%s error_type=%s",
                running.job_id,
                running.product_id,
                running.source_id,
                error.code,
                type(update_error).__name__,
            )
        logger.warning(
            "event=csv_processing.failed job_id=%s product_id=%s source_id=%s error_code=%s",
            running.job_id,
            running.product_id,
            running.source_id,
            error.code,
        )
