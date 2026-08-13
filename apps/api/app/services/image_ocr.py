"""Orchestrate one bounded local image OCR job."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    ImageAnalysisResultRequiredError,
    ImageOcrError,
    ImageOcrObjectNotFoundError,
    ImageOcrObjectStorageError,
    ImageOcrRepositoryError,
    ImageOcrResultStorageError,
    InvalidImageOcrJobError,
    InvalidImageOcrSourceError,
    ObjectNotFoundError,
    ObjectStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.image_analysis import ImageAnalysisResult
from app.domain.image_ocr import ImageOcrQualityStatus, ImageOcrResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSource, ProductSourceType
from app.repositories.image_analysis import ImageAnalysisResultRepository
from app.repositories.image_ocr import ImageOcrResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services.image_inspector import SUPPORTED_MIME_FORMATS
from app.services.image_ocr_pipeline import (
    ImageOcrLimits,
    load_oriented_image,
    recognize_regions,
    select_ocr_regions,
)
from app.services.ocr_engine import OcrEngine
from app.storage.protocol import ObjectStorage

logger = logging.getLogger(__name__)


class ImageOcrService:
    """Recognize bounded text through protocols without classification or extraction."""

    def __init__(
        self,
        job_repository: ProcessingJobRepository,
        source_repository: ProductSourceRepository,
        analysis_repository: ImageAnalysisResultRepository,
        result_repository: ImageOcrResultRepository,
        object_storage: ObjectStorage,
        engine: OcrEngine,
        limits: ImageOcrLimits,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._job_repository = job_repository
        self._source_repository = source_repository
        self._analysis_repository = analysis_repository
        self._result_repository = result_repository
        self._object_storage = object_storage
        self._engine = engine
        self._limits = limits
        self._clock = clock or (lambda: datetime.now(UTC))

    def recognize_for_job(self, *, job_id: UUID) -> ImageOcrResult:
        job = self._job_repository.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.IMAGE_OCR
            or job.status is not ProcessingJobStatus.PENDING
        ):
            raise InvalidImageOcrJobError()
        source = self._source_repository.get_by_id(job.product_id, job.source_id)
        if not self._valid_source(source):
            raise InvalidImageOcrSourceError()
        assert source is not None
        if self._result_repository.get_by_job_id(job.job_id) is not None:
            raise InvalidImageOcrJobError()
        analysis = self._find_analysis(job)
        if analysis is None:
            raise ImageAnalysisResultRequiredError()
        if (
            analysis.product_id != job.product_id
            or analysis.source_id != job.source_id
            or analysis.metadata.mime_type != source.mime_type
            or analysis.metadata.file_size_bytes != source.file_size_bytes
        ):
            raise ImageAnalysisResultRequiredError()
        regions = select_ocr_regions(analysis, self._limits.max_regions)

        logger.info(
            "event=image_ocr.started job_id=%s product_id=%s source_id=%s analysis_id=%s",
            job.job_id,
            job.product_id,
            job.source_id,
            analysis.analysis_id,
        )
        running = self._start_job(job)
        try:
            assert source.storage_key is not None
            assert source.mime_type is not None
            assert source.file_size_bytes is not None
            with self._object_storage.open(source.storage_key) as stream:
                logger.info(
                    "event=image_ocr.image_opened job_id=%s product_id=%s source_id=%s",
                    job.job_id,
                    job.product_id,
                    job.source_id,
                )
                with load_oriented_image(
                    stream,
                    analysis=analysis,
                    expected_mime_type=source.mime_type,
                    expected_size_bytes=source.file_size_bytes,
                ) as image:
                    logger.info(
                        "event=image_ocr.regions_selected job_id=%s product_id=%s "
                        "source_id=%s region_count=%s",
                        job.job_id,
                        job.product_id,
                        job.source_id,
                        len(regions),
                    )
                    evidence = recognize_regions(
                        image,
                        analysis=analysis,
                        regions=regions,
                        engine=self._engine,
                        limits=self._limits,
                    )
            result = ImageOcrResult.create(
                job_id=job.job_id,
                product_id=job.product_id,
                source_id=job.source_id,
                image_analysis_id=analysis.analysis_id,
                engine=self._engine.engine_name,
                engine_version=self._engine.engine_version,
                image_width=evidence.image_width,
                image_height=evidence.image_height,
                region_count=evidence.region_count,
                blocks=evidence.blocks,
                duplicate_block_count=evidence.duplicate_block_count,
                minimum_confidence_bp=self._limits.minimum_confidence_bp,
                now=self._clock(),
            )
            logger.info(
                "event=image_ocr.recognition_completed job_id=%s product_id=%s "
                "source_id=%s engine=%s region_count=%s block_count=%s "
                "duplicate_block_count=%s character_count=%s average_confidence_bp=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                result.engine,
                result.region_count,
                result.block_count,
                result.duplicate_block_count,
                result.total_character_count,
                result.average_confidence_bp,
            )
            if result.quality_status is ImageOcrQualityStatus.NO_TEXT:
                logger.info("event=image_ocr.no_text job_id=%s", job.job_id)
            elif result.quality_status is ImageOcrQualityStatus.LOW_CONFIDENCE_TEXT:
                logger.info("event=image_ocr.low_confidence job_id=%s", job.job_id)
            stored = self._result_repository.create(result)
        except ObjectNotFoundError as exc:
            not_found_error = ImageOcrObjectNotFoundError()
            self._fail_job(running, not_found_error)
            raise not_found_error from exc
        except ObjectStorageError as exc:
            object_storage_error = ImageOcrObjectStorageError()
            self._fail_job(running, object_storage_error)
            raise object_storage_error from exc
        except ImageOcrError as exc:
            self._fail_job(running, exc)
            raise
        except ImageOcrRepositoryError:
            result_storage_error = ImageOcrResultStorageError()
            self._fail_job(running, result_storage_error)
            raise
        except Exception as exc:
            unexpected_error = ImageOcrError()
            self._fail_job(running, unexpected_error)
            raise unexpected_error from exc

        completed = replace(running, result_reference=f"image-ocr-results/{stored.ocr_id}")
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._job_repository.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=image_ocr.completion_consistency_risk job_id=%s product_id=%s "
                "source_id=%s ocr_id=%s",
                job.job_id,
                job.product_id,
                job.source_id,
                stored.ocr_id,
            )
            raise
        logger.info(
            "event=image_ocr.completed job_id=%s product_id=%s source_id=%s ocr_id=%s "
            "quality=%s nameplate_text_status=%s heuristic_score=%s",
            job.job_id,
            job.product_id,
            job.source_id,
            stored.ocr_id,
            stored.quality_status.value,
            stored.nameplate_text_status.value,
            stored.nameplate_heuristic_score,
        )
        return stored

    @staticmethod
    def _valid_source(source: ProductSource | None) -> bool:
        return bool(
            source is not None
            and source.source_type is ProductSourceType.IMAGE
            and source.storage_key is not None
            and source.mime_type in SUPPORTED_MIME_FORMATS
            and source.file_size_bytes is not None
            and source.file_size_bytes > 0
        )

    def _find_analysis(self, job: ProcessingJob) -> ImageAnalysisResult | None:
        cursor: str | None = None
        while True:
            page = self._job_repository.list_by_source(
                job.product_id, job.source_id, limit=100, cursor=cursor
            )
            for candidate in page.items:
                if (
                    candidate.job_type is ProcessingJobType.IMAGE_ANALYSIS
                    and candidate.status is ProcessingJobStatus.COMPLETED
                ):
                    result = self._analysis_repository.get_by_job_id(candidate.job_id)
                    if result is not None:
                        return result
            cursor = page.next_cursor
            if cursor is None:
                return None

    def _start_job(self, job: ProcessingJob) -> ProcessingJob:
        candidate = transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock())
        return self._job_repository.update(candidate, expected_version=job.version)

    def _fail_job(self, running: ProcessingJob, error: ImageOcrError) -> None:
        candidate = replace(running, error_code=error.code, error_message=error.safe_message)
        candidate = transition_processing_job(
            candidate, ProcessingJobStatus.FAILED, now=self._clock()
        )
        try:
            self._job_repository.update(candidate, expected_version=running.version)
        except ProcessingJobRepositoryError as update_error:
            logger.error(
                "event=image_ocr.failure_state_update_failed job_id=%s product_id=%s "
                "source_id=%s error_code=%s error_type=%s",
                running.job_id,
                running.product_id,
                running.source_id,
                error.code,
                type(update_error).__name__,
            )
        logger.warning(
            "event=image_ocr.failed job_id=%s product_id=%s source_id=%s error_code=%s",
            running.job_id,
            running.product_id,
            running.source_id,
            error.code,
        )
