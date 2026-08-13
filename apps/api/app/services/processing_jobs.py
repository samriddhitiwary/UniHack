"""Processing-job create and read application workflows."""

import logging
from uuid import UUID

from app.core.exceptions import (
    ProcessingJobNotFoundError,
    ProcessingJobRepositoryError,
    ProcessingJobTypeNotSupportedForSourceError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductSourceNotFoundError,
    ProductSourceRepositoryError,
)
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobType,
    is_processing_job_type_supported,
)
from app.domain.product_sources import ProductSource
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.repositories.products import ProductRepository
from app.schemas.processing_jobs import ProcessingJobListResult, ProcessingJobRecord

logger = logging.getLogger(__name__)


class ProcessingJobService:
    """Coordinate job metadata workflows without HTTP or infrastructure coupling."""

    def __init__(
        self,
        product_repository: ProductRepository,
        source_repository: ProductSourceRepository,
        job_repository: ProcessingJobRepository,
    ) -> None:
        self._product_repository = product_repository
        self._source_repository = source_repository
        self._job_repository = job_repository

    def create_job(
        self,
        *,
        product_id: UUID,
        source_id: UUID,
        job_type: ProcessingJobType,
    ) -> ProcessingJob:
        logger.info(
            "event=processing_job.create.requested product_id=%s source_id=%s job_type=%s",
            product_id,
            source_id,
            job_type.value,
        )
        self._require_product(product_id)
        source = self._require_source(product_id, source_id)
        if job_type in {
            ProcessingJobType.PRODUCT_CLASSIFICATION,
            ProcessingJobType.ATTRIBUTE_EXTRACTION,
            ProcessingJobType.ATTRIBUTE_NORMALIZATION,
        }:
            raise ProcessingJobTypeNotSupportedForSourceError(
                source.source_type.value,
                job_type.value,
            )
        if not is_processing_job_type_supported(source.source_type, job_type):
            logger.info(
                "event=processing_job.create_rejected product_id=%s source_id=%s "
                "source_type=%s job_type=%s",
                product_id,
                source_id,
                source.source_type.value,
                job_type.value,
            )
            raise ProcessingJobTypeNotSupportedForSourceError(
                source.source_type.value,
                job_type.value,
            )
        job = ProcessingJob.create(
            product_id=product_id,
            source_id=source_id,
            job_type=job_type,
        )
        try:
            stored = self._job_repository.create(job)
        except ProcessingJobRepositoryError as exc:
            self._log_job_failure("create", product_id, source_id, exc)
            raise
        logger.info(
            "event=processing_job.created job_id=%s product_id=%s source_id=%s "
            "job_type=%s status=%s",
            stored.job_id,
            stored.product_id,
            stored.source_id,
            stored.job_type.value,
            stored.status.value,
        )
        return stored

    def get_job(self, *, job_id: UUID) -> ProcessingJob:
        logger.info("event=processing_job.retrieve.requested job_id=%s", job_id)
        try:
            job = self._job_repository.get_by_id(job_id)
        except ProcessingJobRepositoryError as exc:
            self._log_job_failure("retrieve", None, None, exc, job_id=job_id)
            raise
        if job is None:
            logger.info("event=processing_job.not_found job_id=%s", job_id)
            raise ProcessingJobNotFoundError(job_id)
        logger.info("event=processing_job.retrieved job_id=%s", job_id)
        return job

    def list_product_jobs(
        self,
        *,
        product_id: UUID,
        limit: int,
        cursor: str | None = None,
    ) -> ProcessingJobListResult:
        logger.info(
            "event=processing_job.list_product.requested product_id=%s limit=%s has_cursor=%s",
            product_id,
            limit,
            cursor is not None,
        )
        self._require_product(product_id)
        try:
            page = self._job_repository.list_by_product(
                product_id,
                limit=limit,
                cursor=cursor,
            )
        except ProcessingJobRepositoryError as exc:
            self._log_job_failure("list_product", product_id, None, exc)
            raise
        return self._list_result(page.items, page.next_cursor, product_id, None)

    def list_source_jobs(
        self,
        *,
        product_id: UUID,
        source_id: UUID,
        limit: int,
        cursor: str | None = None,
    ) -> ProcessingJobListResult:
        logger.info(
            "event=processing_job.list_source.requested product_id=%s source_id=%s "
            "limit=%s has_cursor=%s",
            product_id,
            source_id,
            limit,
            cursor is not None,
        )
        self._require_product(product_id)
        self._require_source(product_id, source_id)
        try:
            page = self._job_repository.list_by_source(
                product_id,
                source_id,
                limit=limit,
                cursor=cursor,
            )
        except ProcessingJobRepositoryError as exc:
            self._log_job_failure("list_source", product_id, source_id, exc)
            raise
        return self._list_result(page.items, page.next_cursor, product_id, source_id)

    def _require_product(self, product_id: UUID) -> None:
        try:
            product = self._product_repository.get_by_id(product_id)
        except ProductRepositoryError as exc:
            logger.warning(
                "event=processing_job.read_failed operation=product_check product_id=%s "
                "error_type=%s",
                product_id,
                type(exc).__name__,
            )
            raise
        if product is None:
            logger.info("event=processing_job.parent_product_not_found product_id=%s", product_id)
            raise ProductNotFoundError(product_id)

    def _require_source(self, product_id: UUID, source_id: UUID) -> ProductSource:
        try:
            source = self._source_repository.get_by_id(product_id, source_id)
        except ProductSourceRepositoryError as exc:
            logger.warning(
                "event=processing_job.read_failed operation=source_check product_id=%s "
                "source_id=%s error_type=%s",
                product_id,
                source_id,
                type(exc).__name__,
            )
            raise
        if source is None:
            logger.info(
                "event=processing_job.parent_source_not_found product_id=%s source_id=%s",
                product_id,
                source_id,
            )
            raise ProductSourceNotFoundError(product_id, source_id)
        return source

    @staticmethod
    def _list_result(
        jobs: tuple[ProcessingJob, ...],
        next_cursor: str | None,
        product_id: UUID,
        source_id: UUID | None,
    ) -> ProcessingJobListResult:
        result = ProcessingJobListResult(
            items=[ProcessingJobRecord.model_validate(job) for job in jobs],
            next_cursor=next_cursor,
        )
        logger.info(
            "event=processing_job.listed product_id=%s source_id=%s result_count=%s "
            "has_next_cursor=%s",
            product_id,
            source_id,
            len(result.items),
            result.next_cursor is not None,
        )
        return result

    @staticmethod
    def _log_job_failure(
        operation: str,
        product_id: UUID | None,
        source_id: UUID | None,
        error: Exception,
        *,
        job_id: UUID | None = None,
    ) -> None:
        logger.warning(
            "event=processing_job.read_failed operation=%s job_id=%s product_id=%s "
            "source_id=%s error_type=%s",
            operation,
            job_id,
            product_id,
            source_id,
            type(error).__name__,
        )
