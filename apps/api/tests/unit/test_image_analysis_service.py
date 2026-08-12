"""Image-analysis orchestration and lifecycle tests."""

import inspect
from dataclasses import replace
from io import BytesIO
from typing import BinaryIO, cast
from uuid import UUID

import pytest

from app.core.exceptions import (
    ImageAnalysisPixelLimitExceededError,
    ImageAnalysisRepositoryError,
    ImageDecodeError,
    ImageFormatMismatchError,
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
    ProcessingJobPage,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSource, ProductSourcePage, ProductSourceType
from app.repositories.image_analysis import ImageAnalysisResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services import image_analysis as service_module
from app.services.image_analysis import ImageAnalysisService
from app.services.image_inspector import ImageInspector, InspectedImage
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage
from tests.fixtures.image_analysis import make_image_analysis_result
from tests.fixtures.processing_jobs import (
    JOB_COMPLETED_AT,
    JOB_ID,
    JOB_STARTED_AT,
    make_processing_job,
)
from tests.fixtures.product_sources import SOURCE_ID, make_product_source
from tests.fixtures.products import PRODUCT_ID, SECOND_PRODUCT_ID


class FakeJobs:
    def __init__(self, job: ProcessingJob | None, events: list[str]) -> None:
        self.job, self.events = job, events
        self.updates: list[tuple[ProcessingJob, int]] = []
        self.update_errors: dict[int, Exception] = {}

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        return self.job if self.job and self.job.job_id == job_id else None

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

    def list_by_source(
        self, product_id: UUID, source_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProcessingJobPage:
        raise NotImplementedError


class FakeSources:
    def __init__(self, source: ProductSource | None) -> None:
        self.source = source
        self.calls: list[tuple[UUID, UUID]] = []

    def get_by_id(self, product_id: UUID, source_id: UUID) -> ProductSource | None:
        self.calls.append((product_id, source_id))
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


class FakeStorage:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.error: Exception | None = None
        self.stream: BytesIO | None = None

    def open(self, object_key: str) -> BinaryIO:
        self.events.append("storage:open")
        if self.error:
            raise self.error
        self.stream = BytesIO(b"image")
        return self.stream

    def save(self, *, object_key: str, stream: BinaryIO, max_size_bytes: int) -> StoredObject:
        raise NotImplementedError

    def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    def get_metadata(self, object_key: str) -> StoredObject:
        raise NotImplementedError

    def delete(self, object_key: str) -> None:
        raise NotImplementedError


class FakeInspector:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.error: Exception | None = None
        result = make_image_analysis_result()
        self.output = InspectedImage(result.metadata, result.regions)
        self.calls: list[tuple[str, int | None]] = []

    def inspect(
        self, stream: BinaryIO, *, expected_mime_type: str, expected_size_bytes: int | None = None
    ) -> InspectedImage:
        self.events.append("inspector:inspect")
        self.calls.append((expected_mime_type, expected_size_bytes))
        assert not stream.closed
        if self.error:
            raise self.error
        return self.output


class FakeResults:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.existing: ImageAnalysisResult | None = None
        self.create_error: Exception | None = None
        self.get_error: Exception | None = None
        self.created: list[ImageAnalysisResult] = []

    def create(self, result: ImageAnalysisResult) -> ImageAnalysisResult:
        self.events.append("result:create")
        self.created.append(result)
        if self.create_error:
            raise self.create_error
        self.existing = result
        return result

    def get_by_id(self, analysis_id: UUID) -> ImageAnalysisResult | None:
        return self.existing if self.existing and self.existing.analysis_id == analysis_id else None

    def get_by_job_id(self, job_id: UUID) -> ImageAnalysisResult | None:
        if self.get_error:
            raise self.get_error
        return self.existing if self.existing and self.existing.job_id == job_id else None


def pending_job() -> ProcessingJob:
    return make_processing_job(job_type=ProcessingJobType.IMAGE_ANALYSIS)


def image_source(**changes: object) -> ProductSource:
    values: dict[str, object] = {
        "source_type": ProductSourceType.IMAGE,
        "original_filename": "nameplate.png",
        "mime_type": "image/png",
        "file_size_bytes": 100,
        "storage_key": f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/nameplate.png",
    }
    values.update(changes)
    return make_product_source(**values)  # type: ignore[arg-type]


Parts = tuple[FakeJobs, FakeSources, FakeStorage, FakeResults, FakeInspector, list[str]]


def parts() -> Parts:
    events: list[str] = []
    return (
        FakeJobs(pending_job(), events),
        FakeSources(image_source()),
        FakeStorage(events),
        FakeResults(events),
        FakeInspector(events),
        events,
    )


def build(value: Parts) -> ImageAnalysisService:
    jobs, sources, storage, results, inspector, _ = value
    return ImageAnalysisService(
        cast(ProcessingJobRepository, jobs),
        cast(ProductSourceRepository, sources),
        cast(ObjectStorage, storage),
        cast(ImageAnalysisResultRepository, results),
        cast(ImageInspector, inspector),
        clock=lambda: JOB_STARTED_AT,
    )


def test_success_orders_work_persists_then_completes_and_preserves_source() -> None:
    value = parts()
    jobs, sources, storage, _, inspector, events = value
    original = sources.source
    result = build(value).analyze_for_job(job_id=JOB_ID)
    assert events == [
        "job:RUNNING",
        "storage:open",
        "inspector:inspect",
        "result:create",
        "job:COMPLETED",
    ]
    completed = jobs.updates[-1][0]
    assert jobs.updates[0][0].started_at == JOB_STARTED_AT
    assert completed.progress_percent == 100 and completed.completed_at == JOB_STARTED_AT
    assert completed.result_reference == f"image-analysis-results/{result.analysis_id}"
    assert completed.error_code is completed.error_message is None
    assert inspector.calls == [("image/png", 100)] and sources.source == original
    assert storage.stream is not None and storage.stream.closed


@pytest.mark.parametrize(
    "job",
    [
        make_processing_job(job_type=ProcessingJobType.CSV_PROCESSING),
        transition_processing_job(pending_job(), ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT),
        transition_processing_job(
            transition_processing_job(
                pending_job(), ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT
            ),
            ProcessingJobStatus.COMPLETED,
            now=JOB_COMPLETED_AT,
        ),
        transition_processing_job(
            transition_processing_job(
                pending_job(), ProcessingJobStatus.RUNNING, now=JOB_STARTED_AT
            ),
            ProcessingJobStatus.FAILED,
            now=JOB_COMPLETED_AT,
        ),
        transition_processing_job(pending_job(), ProcessingJobStatus.CANCELLED, now=JOB_STARTED_AT),
    ],
)
def test_wrong_type_and_nonpending_jobs_rejected(job: ProcessingJob) -> None:
    value = parts()
    value[0].job = job
    with pytest.raises(InvalidImageAnalysisJobError):
        build(value).analyze_for_job(job_id=JOB_ID)
    assert value[0].updates == []


def test_missing_job_stops_before_source() -> None:
    value = parts()
    value[0].job = None
    with pytest.raises(InvalidImageAnalysisJobError):
        build(value).analyze_for_job(job_id=JOB_ID)
    assert value[1].calls == []


@pytest.mark.parametrize(
    "source",
    [
        None,
        image_source(product_id=SECOND_PRODUCT_ID),
        image_source(
            source_type=ProductSourceType.CSV, original_filename="x.csv", mime_type="text/csv"
        ),
        image_source(storage_key=None),
        image_source(mime_type=None),
    ],
)
def test_invalid_source_rejected_before_running(source: ProductSource | None) -> None:
    value = parts()
    value[1].source = source
    with pytest.raises(InvalidImageSourceError):
        build(value).analyze_for_job(job_id=JOB_ID)
    assert value[0].updates == []


def test_existing_result_and_lookup_failure_do_not_start() -> None:
    value = parts()
    value[3].existing = make_image_analysis_result()
    with pytest.raises(InvalidImageAnalysisJobError):
        build(value).analyze_for_job(job_id=JOB_ID)
    value = parts()
    value[3].get_error = ImageAnalysisRepositoryError("private")
    with pytest.raises(ImageAnalysisRepositoryError):
        build(value).analyze_for_job(job_id=JOB_ID)
    assert value[0].updates == []


@pytest.mark.parametrize(
    "error",
    [ImageDecodeError(), ImageFormatMismatchError(), ImageAnalysisPixelLimitExceededError()],
)
def test_inspector_failures_mark_running_job_failed(error: Exception) -> None:
    value = parts()
    value[4].error = error
    with pytest.raises(type(error)):
        build(value).analyze_for_job(job_id=JOB_ID)
    failed = value[0].updates[-1][0]
    assert failed.status is ProcessingJobStatus.FAILED and failed.error_code == error.code  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("error", "raised", "code"),
    [
        (ObjectNotFoundError("private"), ImageObjectNotFoundError, "IMAGE_OBJECT_NOT_FOUND"),
        (ObjectStorageError("private"), ImageObjectStorageError, "IMAGE_OBJECT_STORAGE_FAILED"),
    ],
)
def test_storage_failures_are_safe(error: Exception, raised: type[Exception], code: str) -> None:
    value = parts()
    value[2].error = error
    with pytest.raises(raised):
        build(value).analyze_for_job(job_id=JOB_ID)
    failed = value[0].updates[-1][0]
    assert failed.error_code == code and "private" not in (failed.error_message or "")


def test_repository_failure_marks_failed_and_preserves_error() -> None:
    value = parts()
    value[3].create_error = ImageAnalysisRepositoryError("private")
    with pytest.raises(ImageAnalysisRepositoryError):
        build(value).analyze_for_job(job_id=JOB_ID)
    assert value[0].updates[-1][0].error_code == "IMAGE_ANALYSIS_STORAGE_FAILED"


def test_completion_failure_keeps_result_and_logs_risk(caplog: pytest.LogCaptureFixture) -> None:
    value = parts()
    value[0].update_errors[2] = ProcessingJobRepositoryError("failed")
    with pytest.raises(ProcessingJobRepositoryError):
        build(value).analyze_for_job(job_id=JOB_ID)
    assert len(value[3].created) == 1 and value[0].job is not None
    assert value[0].job.status is ProcessingJobStatus.RUNNING
    assert "image_analysis.completion_consistency_risk" in caplog.text


def test_failure_update_does_not_mask_inspector_error() -> None:
    value = parts()
    value[0].update_errors[2] = ProcessingJobRepositoryError("failed")
    value[4].error = ImageDecodeError()
    with pytest.raises(ImageDecodeError):
        build(value).analyze_for_job(job_id=JOB_ID)


def test_service_has_no_http_boto3_filesystem_ocr_or_execution_logic() -> None:
    source = inspect.getsource(service_module).lower()
    for forbidden in (
        "fastapi",
        "boto3",
        "pathlib",
        "localobjectstorage",
        "subprocess",
        "pytesseract",
        "easyocr",
        "ocr",
    ):
        if forbidden == "ocr":
            assert "no ocr" in source
        else:
            assert forbidden not in source
