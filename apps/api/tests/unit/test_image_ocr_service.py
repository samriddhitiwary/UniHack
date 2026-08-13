"""Image OCR orchestration, lifecycle, dependency, and failure tests."""

import inspect
from dataclasses import replace
from io import BytesIO
from typing import BinaryIO, cast
from uuid import UUID

import pytest
from PIL import Image

from app.core.exceptions import (
    ImageAnalysisResultRequiredError,
    ImageOcrEngineError,
    ImageOcrObjectNotFoundError,
    ImageOcrObjectStorageError,
    ImageOcrRepositoryError,
    ImageOcrTextLimitExceededError,
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
    ProcessingJobPage,
    ProcessingJobStatus,
    ProcessingJobType,
)
from app.domain.product_sources import ProductSource, ProductSourcePage, ProductSourceType
from app.repositories.image_analysis import ImageAnalysisResultRepository
from app.repositories.image_ocr import ImageOcrResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services import image_ocr as service_module
from app.services.image_ocr import ImageOcrService
from app.services.image_ocr_pipeline import ImageOcrLimits
from app.services.ocr_engine import OcrEngine, OcrEngineBlock
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage
from tests.fixtures.image_analysis import make_image_analysis_result, make_image_bytes
from tests.fixtures.processing_jobs import (
    JOB_COMPLETED_AT,
    JOB_ID,
    JOB_STARTED_AT,
    SECOND_JOB_ID,
    make_processing_job,
)
from tests.fixtures.product_sources import SOURCE_ID, make_product_source
from tests.fixtures.products import PRODUCT_ID, SECOND_PRODUCT_ID


class FakeJobs:
    def __init__(self, job: ProcessingJob, analysis_job: ProcessingJob, events: list[str]) -> None:
        self.job, self.analysis_job, self.events = job, analysis_job, events
        self.updates: list[tuple[ProcessingJob, int]] = []
        self.update_errors: dict[int, Exception] = {}
        self.pages: list[ProcessingJobPage] | None = None

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        return self.job if self.job.job_id == job_id else None

    def list_by_source(
        self, product_id: UUID, source_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProcessingJobPage:
        self.events.append("jobs:list-source")
        if self.pages is not None:
            return self.pages.pop(0)
        return ProcessingJobPage((self.analysis_job,), None)

    def update(self, job: ProcessingJob, expected_version: int) -> ProcessingJob:
        self.updates.append((job, expected_version))
        self.events.append(f"job:{job.status.value}")
        if len(self.updates) in self.update_errors:
            raise self.update_errors[len(self.updates)]
        self.job = replace(job, version=expected_version + 1, updated_at=JOB_STARTED_AT)
        return self.job

    def create(self, job: ProcessingJob) -> ProcessingJob:
        raise NotImplementedError

    def list_by_product(
        self, product_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProcessingJobPage:
        raise NotImplementedError


class FakeSources:
    def __init__(self, source: ProductSource | None) -> None:
        self.source = source

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None:
        if self.source and (self.source.product_id, self.source.source_id) == (
            product_id,
            source_id,
        ):
            return self.source
        return None

    def create(self, source: ProductSource) -> ProductSource:
        raise NotImplementedError

    def update(self, source: ProductSource, expected_version: int) -> ProductSource:
        raise NotImplementedError

    def list_by_product(
        self, product_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProductSourcePage:
        raise NotImplementedError

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeAnalysisResults:
    def __init__(self, result: ImageAnalysisResult | None) -> None:
        self.result = result

    def get_by_job_id(self, job_id: UUID) -> ImageAnalysisResult | None:
        return self.result if self.result and self.result.job_id == job_id else None

    def get_by_id(self, analysis_id: UUID) -> ImageAnalysisResult | None:
        return self.result if self.result and self.result.analysis_id == analysis_id else None

    def create(self, result: ImageAnalysisResult) -> ImageAnalysisResult:
        raise NotImplementedError


class FakeOcrResults:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.existing: ImageOcrResult | None = None
        self.error: Exception | None = None
        self.created: list[ImageOcrResult] = []

    def get_by_job_id(self, job_id: UUID) -> ImageOcrResult | None:
        return self.existing if self.existing and self.existing.job_id == job_id else None

    def get_by_id(self, ocr_id: UUID) -> ImageOcrResult | None:
        return self.existing if self.existing and self.existing.ocr_id == ocr_id else None

    def create(self, result: ImageOcrResult) -> ImageOcrResult:
        self.events.append("result:create")
        self.created.append(result)
        if self.error:
            raise self.error
        self.existing = result
        return result


class FakeStorage:
    def __init__(self, data: bytes, events: list[str]) -> None:
        self.data, self.events = data, events
        self.error: Exception | None = None

    def open(self, object_key: str) -> BinaryIO:
        self.events.append("storage:open")
        if self.error:
            raise self.error
        return BytesIO(self.data)

    def save(self, *, object_key: str, stream: BinaryIO, max_size_bytes: int) -> StoredObject:
        raise NotImplementedError

    def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    def get_metadata(self, object_key: str) -> StoredObject:
        raise NotImplementedError

    def delete(self, object_key: str) -> None:
        raise NotImplementedError


class FakeEngine:
    engine_name = "FakeOCR"
    engine_version = "1"

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.blocks: tuple[OcrEngineBlock, ...] = (
            OcrEngineBlock(
                text="MOTOR 415 V",
                confidence_bp=9_000,
                x=10,
                y=10,
                width=80,
                height=20,
            ),
        )
        self.error: Exception | None = None
        self.calls = 0

    def recognize(self, image: Image.Image) -> tuple[OcrEngineBlock, ...]:
        self.events.append("engine:recognize")
        self.calls += 1
        if self.error:
            raise self.error
        return self.blocks


Parts = tuple[
    FakeJobs,
    FakeSources,
    FakeAnalysisResults,
    FakeOcrResults,
    FakeStorage,
    FakeEngine,
    list[str],
]


def parts() -> Parts:
    events: list[str] = []
    data = make_image_bytes()
    analysis = make_image_analysis_result()
    analysis = replace(analysis, metadata=replace(analysis.metadata, file_size_bytes=len(data)))
    ocr_job = make_processing_job(job_id=SECOND_JOB_ID, job_type=ProcessingJobType.IMAGE_OCR)
    analysis_job = make_processing_job(
        job_id=JOB_ID,
        job_type=ProcessingJobType.IMAGE_ANALYSIS,
        status=ProcessingJobStatus.COMPLETED,
        progress_percent=100,
        result_reference=f"image-analysis-results/{analysis.analysis_id}",
        started_at=JOB_STARTED_AT,
        completed_at=JOB_COMPLETED_AT,
        updated_at=JOB_COMPLETED_AT,
    )
    source = make_product_source(
        source_type=ProductSourceType.IMAGE,
        original_filename="nameplate.png",
        storage_key=f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/nameplate.png",
        mime_type="image/png",
        file_size_bytes=len(data),
    )
    return (
        FakeJobs(ocr_job, analysis_job, events),
        FakeSources(source),
        FakeAnalysisResults(analysis),
        FakeOcrResults(events),
        FakeStorage(data, events),
        FakeEngine(events),
        events,
    )


def build(value: Parts, *, limits: ImageOcrLimits | None = None) -> ImageOcrService:
    jobs, sources, analyses, results, storage, engine, _ = value
    return ImageOcrService(
        cast(ProcessingJobRepository, jobs),
        cast(ProductSourceRepository, sources),
        cast(ImageAnalysisResultRepository, analyses),
        cast(ImageOcrResultRepository, results),
        cast(ObjectStorage, storage),
        cast(OcrEngine, engine),
        limits or ImageOcrLimits(),
        clock=lambda: JOB_STARTED_AT,
    )


def test_success_reuses_analysis_runs_before_persist_and_completes() -> None:
    value = parts()
    original_source = value[1].source
    result = build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert value[6][:4] == ["jobs:list-source", "job:RUNNING", "storage:open", "engine:recognize"]
    assert value[6][-2:] == ["result:create", "job:COMPLETED"]
    completed = value[0].updates[-1][0]
    assert value[0].updates[0][0].started_at == JOB_STARTED_AT
    assert completed.progress_percent == 100 and completed.completed_at == JOB_STARTED_AT
    assert completed.result_reference == f"image-ocr-results/{result.ocr_id}"
    assert result.image_analysis_id == value[2].result.analysis_id  # type: ignore[union-attr]
    assert value[1].source == original_source


@pytest.mark.parametrize(
    "job",
    [
        make_processing_job(job_id=SECOND_JOB_ID, job_type=ProcessingJobType.IMAGE_ANALYSIS),
        make_processing_job(
            job_id=SECOND_JOB_ID,
            job_type=ProcessingJobType.IMAGE_OCR,
            status=ProcessingJobStatus.RUNNING,
            started_at=JOB_STARTED_AT,
        ),
        make_processing_job(
            job_id=SECOND_JOB_ID,
            job_type=ProcessingJobType.IMAGE_OCR,
            status=ProcessingJobStatus.COMPLETED,
            progress_percent=100,
            started_at=JOB_STARTED_AT,
            completed_at=JOB_COMPLETED_AT,
        ),
        make_processing_job(
            job_id=SECOND_JOB_ID,
            job_type=ProcessingJobType.IMAGE_OCR,
            status=ProcessingJobStatus.FAILED,
            started_at=JOB_STARTED_AT,
            completed_at=JOB_COMPLETED_AT,
        ),
        make_processing_job(
            job_id=SECOND_JOB_ID,
            job_type=ProcessingJobType.IMAGE_OCR,
            status=ProcessingJobStatus.CANCELLED,
            completed_at=JOB_COMPLETED_AT,
        ),
    ],
)
def test_wrong_type_or_nonpending_jobs_are_rejected(job: ProcessingJob) -> None:
    value = parts()
    value[0].job = job
    with pytest.raises(InvalidImageOcrJobError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert value[0].updates == []


def test_missing_job_is_rejected() -> None:
    value = parts()
    value[0].job = replace(value[0].job, job_id=JOB_ID)
    with pytest.raises(InvalidImageOcrJobError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)


@pytest.mark.parametrize(
    "source",
    [
        None,
        make_product_source(product_id=SECOND_PRODUCT_ID),
        make_product_source(source_type=ProductSourceType.PDF),
        make_product_source(
            source_type=ProductSourceType.IMAGE,
            mime_type="image/png",
            original_filename="x.png",
            storage_key=None,
        ),
    ],
)
def test_invalid_sources_fail_before_running(source: ProductSource | None) -> None:
    value = parts()
    value[1].source = source
    with pytest.raises(InvalidImageOcrSourceError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert value[0].updates == []


def test_missing_analysis_and_existing_ocr_result_fail_before_running() -> None:
    value = parts()
    value[2].result = None
    with pytest.raises(ImageAnalysisResultRequiredError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    value = parts()
    value[3].existing = make_image_ocr_result_for_job(value[0].job.job_id)
    with pytest.raises(InvalidImageOcrJobError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)


def test_analysis_lookup_paginates_source_history_without_scan() -> None:
    value = parts()
    value[0].pages = [
        ProcessingJobPage((value[0].job,), "next"),
        ProcessingJobPage((value[0].analysis_job,), None),
    ]
    result = build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert result.image_analysis_id == value[2].result.analysis_id  # type: ignore[union-attr]
    assert value[6].count("jobs:list-source") == 2


def make_image_ocr_result_for_job(job_id: UUID) -> ImageOcrResult:
    from tests.fixtures.image_ocr import make_image_ocr_result

    return replace(make_image_ocr_result(), job_id=job_id)


@pytest.mark.parametrize(
    ("blocks", "quality"),
    [
        ((), ImageOcrQualityStatus.NO_TEXT),
        (
            (
                OcrEngineBlock(
                    text="weak",
                    confidence_bp=1_000,
                    x=1,
                    y=1,
                    width=20,
                    height=10,
                ),
            ),
            ImageOcrQualityStatus.LOW_CONFIDENCE_TEXT,
        ),
    ],
)
def test_no_text_and_low_confidence_are_completed(blocks, quality) -> None:
    value = parts()
    value[5].blocks = blocks
    result = build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert result.quality_status is quality
    assert value[0].updates[-1][0].status is ProcessingJobStatus.COMPLETED


@pytest.mark.parametrize(
    ("error", "raised", "code"),
    [
        (ObjectNotFoundError("private"), ImageOcrObjectNotFoundError, "IMAGE_OCR_OBJECT_NOT_FOUND"),
        (
            ObjectStorageError("private"),
            ImageOcrObjectStorageError,
            "IMAGE_OCR_OBJECT_STORAGE_FAILED",
        ),
    ],
)
def test_storage_failures_are_safe(error: Exception, raised: type[Exception], code: str) -> None:
    value = parts()
    value[4].error = error
    with pytest.raises(raised):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    failed = value[0].updates[-1][0]
    assert failed.status is ProcessingJobStatus.FAILED and failed.error_code == code
    assert "private" not in (failed.error_message or "")


def test_engine_and_limit_failures_mark_failed() -> None:
    value = parts()
    value[5].error = ImageOcrEngineError()
    with pytest.raises(ImageOcrEngineError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert value[0].updates[-1][0].error_code == "IMAGE_OCR_ENGINE_FAILED"
    value = parts()
    value[5].blocks = (
        OcrEngineBlock(text="long", confidence_bp=9_000, x=1, y=1, width=10, height=10),
    )
    with pytest.raises(ImageOcrTextLimitExceededError):
        build(
            value,
            limits=ImageOcrLimits(max_block_characters=2),
        ).recognize_for_job(job_id=SECOND_JOB_ID)
    assert value[0].updates[-1][0].status is ProcessingJobStatus.FAILED


def test_repository_failure_marks_failed_and_result_precedes_completion() -> None:
    value = parts()
    value[3].error = ImageOcrRepositoryError("private")
    with pytest.raises(ImageOcrRepositoryError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert value[0].updates[-1][0].error_code == "IMAGE_OCR_STORAGE_FAILED"
    assert "job:COMPLETED" not in value[6]


def test_completion_failure_preserves_result_and_logs_risk(
    caplog: pytest.LogCaptureFixture,
) -> None:
    value = parts()
    value[0].update_errors[2] = ProcessingJobRepositoryError("failed")
    with pytest.raises(ProcessingJobRepositoryError):
        build(value).recognize_for_job(job_id=SECOND_JOB_ID)
    assert len(value[3].created) == 1 and value[0].job.status is ProcessingJobStatus.RUNNING
    assert "image_ocr.completion_consistency_risk" in caplog.text


def test_service_has_no_fastapi_boto3_filesystem_hosted_ai_or_classification_logic() -> None:
    source = inspect.getsource(service_module).lower()
    for forbidden in (
        "fastapi",
        "boto3",
        "pathlib",
        "localobjectstorage",
        "subprocess",
        "openai",
        "textract",
        "product_classifier",
        "attribute_extractor",
    ):
        assert forbidden not in source
