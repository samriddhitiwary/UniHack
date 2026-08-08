"""Orchestrate one bounded PDF table-extraction job."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    InvalidPdfTableExtractionJobError,
    InvalidPdfTableSourceError,
    ObjectNotFoundError,
    ObjectStorageError,
    PdfTableExtractionError,
    PdfTableExtractionObjectNotFoundError,
    PdfTableExtractionObjectStorageError,
    PdfTableExtractionRepositoryError,
    PdfTableExtractionResultStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.pdf_table_extraction import (
    PdfTableExtractionQualityStatus,
    PdfTableExtractionResult,
)
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSourceType
from app.repositories.pdf_table_extraction import PdfTableExtractionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services.pdf_table_parser import PARSER_NAME, PARSER_VERSION, PdfTableParser
from app.storage.protocol import ObjectStorage

logger = logging.getLogger(__name__)


class PdfTableExtractionService:
    """Run table extraction through repository and storage protocols; no worker or API."""

    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        source_repository: ProductSourceRepository,
        object_storage: ObjectStorage,
        result_repository: PdfTableExtractionRepository,
        parser: PdfTableParser,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._source_repository = source_repository
        self._object_storage = object_storage
        self._result_repository = result_repository
        self._parser = parser
        self._clock = clock or (lambda: datetime.now(UTC))

    def extract_for_job(self, *, job_id: UUID) -> PdfTableExtractionResult:
        job = self._job_repository.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.PDF_TABLE_EXTRACTION
            or job.status is not ProcessingJobStatus.PENDING
        ):
            raise InvalidPdfTableExtractionJobError()
        source = self._source_repository.get_by_id(job.product_id, job.source_id)
        if (
            source is None
            or source.source_type is not ProductSourceType.PDF
            or source.storage_key is None
        ):
            raise InvalidPdfTableSourceError()
        if self._result_repository.get_by_job_id(job.job_id) is not None:
            raise InvalidPdfTableExtractionJobError()

        logger.info(
            "event=pdf_table_extraction.started job_id=%s product_id=%s source_id=%s "
            "parser=%s parser_version=%s",
            job.job_id,
            job.product_id,
            job.source_id,
            PARSER_NAME,
            PARSER_VERSION,
        )
        running = self._start_job(job)
        try:
            with self._object_storage.open(source.storage_key) as stream:
                logger.info(
                    "event=pdf_table_extraction.pdf_opened job_id=%s product_id=%s source_id=%s",
                    job.job_id,
                    job.product_id,
                    job.source_id,
                )
                output = self._parser.extract_tables(stream)
            result = PdfTableExtractionResult.create(
                job_id=job.job_id,
                product_id=job.product_id,
                source_id=job.source_id,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
                page_count=output.page_count,
                tables=output.tables,
                warning_codes=output.warning_codes,
                now=self._clock(),
            )
            stored = self._result_repository.create(result)
        except ObjectNotFoundError as exc:
            error = PdfTableExtractionObjectNotFoundError()
            self._fail_job(running, error)
            raise error from exc
        except ObjectStorageError as exc:
            storage_error = PdfTableExtractionObjectStorageError()
            self._fail_job(running, storage_error)
            raise storage_error from exc
        except PdfTableExtractionError as exc:
            self._fail_job(running, exc)
            raise
        except PdfTableExtractionRepositoryError:
            result_error = PdfTableExtractionResultStorageError()
            self._fail_job(running, result_error)
            raise
        except Exception as exc:
            unexpected_error = PdfTableExtractionError()
            self._fail_job(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(
            running, result_reference=f"table-extraction-results/{stored.extraction_id}"
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._job_repository.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=pdf_table_extraction.completion_consistency_risk job_id=%s "
                "product_id=%s source_id=%s extraction_id=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                stored.extraction_id,
            )
            raise

        event = {
            PdfTableExtractionQualityStatus.TABLES_FOUND: "pdf_table_extraction.tables_found",
            PdfTableExtractionQualityStatus.NO_TABLES: "pdf_table_extraction.no_tables",
            PdfTableExtractionQualityStatus.PARTIAL: "pdf_table_extraction.partial",
        }[stored.quality_status]
        logger.info(
            "event=%s job_id=%s product_id=%s source_id=%s page_count=%s "
            "pages_with_tables=%s table_count=%s total_rows=%s total_cells=%s "
            "quality_status=%s",
            event,
            job.job_id,
            job.product_id,
            job.source_id,
            stored.page_count,
            stored.pages_with_tables,
            stored.table_count,
            stored.total_row_count,
            stored.total_cell_count,
            stored.quality_status.value,
        )
        return stored

    def _start_job(self, job: ProcessingJob) -> ProcessingJob:
        candidate = transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock())
        return self._job_repository.update(candidate, expected_version=job.version)

    def _fail_job(self, running: ProcessingJob, error: PdfTableExtractionError) -> None:
        candidate = replace(running, error_code=error.code, error_message=error.safe_message)
        candidate = transition_processing_job(
            candidate, ProcessingJobStatus.FAILED, now=self._clock()
        )
        try:
            self._job_repository.update(candidate, expected_version=running.version)
        except ProcessingJobRepositoryError as update_error:
            logger.error(
                "event=pdf_table_extraction.failure_state_update_failed job_id=%s "
                "product_id=%s source_id=%s error_code=%s error_type=%s",
                running.job_id,
                running.product_id,
                running.source_id,
                error.code,
                type(update_error).__name__,
            )
        logger.warning(
            "event=pdf_table_extraction.failed job_id=%s product_id=%s source_id=%s error_code=%s",
            running.job_id,
            running.product_id,
            running.source_id,
            error.code,
        )
