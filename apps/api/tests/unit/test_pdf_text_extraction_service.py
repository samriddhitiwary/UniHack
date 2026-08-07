"""PDF text-extraction orchestration and lifecycle tests."""

import inspect
from dataclasses import replace
from io import BytesIO
from typing import BinaryIO, cast
from uuid import UUID

import pytest

from app.core.exceptions import (
    InvalidPdfExtractionJobError,
    InvalidPdfSourceError,
    ObjectNotFoundError,
    ObjectStorageError,
    PdfExtractionObjectNotFoundError,
    PdfExtractionObjectStorageError,
    PdfExtractionPageLimitExceededError,
    PdfExtractionRepositoryError,
    PdfExtractionTextLimitExceededError,
    PdfParseError,
    PdfTextExtractionError,
    ProcessingJobRepositoryError,
)
from app.domain.pdf_extraction import PdfExtractionPage, PdfTextExtractionResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobPage,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSource, ProductSourcePage, ProductSourceType
from app.repositories.pdf_extraction import PdfExtractionResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services import pdf_text_extraction as service_module
from app.services.pdf_text_extraction import PdfTextExtractionService
from app.services.pdf_text_parser import PdfTextParser
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage
from tests.fixtures.pdf_extraction import make_pdf_extraction_result
from tests.fixtures.processing_jobs import (
    JOB_COMPLETED_AT,
    JOB_ID,
    JOB_STARTED_AT,
    make_processing_job,
)
from tests.fixtures.product_sources import SOURCE_ID, make_product_source
from tests.fixtures.products import PRODUCT_ID, SECOND_PRODUCT_ID


class FakeJobs:
    def __init__(
        self,
        job: ProcessingJob | None,
        events: list[str],
        *,
        update_errors: dict[int, Exception] | None = None,
    ) -> None:
        self.job = job
        self.events = events
        self.update_errors = update_errors or {}
        self.updates: list[tuple[ProcessingJob, int]] = []

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        return self.job if self.job and self.job.job_id == job_id else None

    def update(self, job: ProcessingJob, expected_version: int) -> ProcessingJob:
        self.updates.append((job, expected_version))
        call_number = len(self.updates)
        self.events.append(f"job:{job.status.value}")
        if call_number in self.update_errors:
            raise self.update_errors[call_number]
        stored = replace(job, version=expected_version + 1, updated_at=JOB_STARTED_AT)
        self.job = stored
        return stored

    def create(self, job: ProcessingJob) -> ProcessingJob:
        raise NotImplementedError

    def list_by_product(
        self, product_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProcessingJobPage:
        raise NotImplementedError

    def list_by_source(
        self,
        product_id: UUID,
        source_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
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
        self,
        product_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProductSourcePage:
        raise NotImplementedError

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeStorage:
    def __init__(
        self,
        events: list[str],
        *,
        content: bytes = b"pdf",
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.content = content
        self.error = error
        self.opened: list[str] = []
        self.last_stream: BytesIO | None = None

    def open(self, object_key: str) -> BinaryIO:
        self.events.append("storage:open")
        self.opened.append(object_key)
        if self.error:
            raise self.error
        self.last_stream = BytesIO(self.content)
        return self.last_stream

    def save(self, *, object_key: str, stream: BinaryIO, max_size_bytes: int) -> StoredObject:
        raise NotImplementedError

    def exists(self, object_key: str) -> bool:
        raise NotImplementedError

    def get_metadata(self, object_key: str) -> StoredObject:
        raise NotImplementedError

    def delete(self, object_key: str) -> None:
        raise NotImplementedError


class FakeParser:
    def __init__(
        self,
        events: list[str],
        pages: tuple[PdfExtractionPage, ...],
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.pages = pages
        self.error = error

    def extract_pages(self, stream: BinaryIO) -> tuple[PdfExtractionPage, ...]:
        self.events.append("parser:extract")
        assert not stream.closed
        if self.error:
            raise self.error
        return self.pages


class FakeResults:
    def __init__(
        self,
        events: list[str],
        *,
        existing: PdfTextExtractionResult | None = None,
        create_error: Exception | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.existing = existing
        self.create_error = create_error
        self.get_error = get_error
        self.created: list[PdfTextExtractionResult] = []

    def create(self, result: PdfTextExtractionResult) -> PdfTextExtractionResult:
        self.events.append("result:create")
        self.created.append(result)
        if self.create_error:
            raise self.create_error
        self.existing = result
        return result

    def get_by_id(self, extraction_id: UUID) -> PdfTextExtractionResult | None:
        return (
            self.existing
            if self.existing and self.existing.extraction_id == extraction_id
            else None
        )

    def get_by_job_id(self, job_id: UUID) -> PdfTextExtractionResult | None:
        if self.get_error:
            raise self.get_error
        return self.existing if self.existing and self.existing.job_id == job_id else None


def pending_job() -> ProcessingJob:
    return make_processing_job(job_type=ProcessingJobType.PDF_TEXT_EXTRACTION)


def pdf_source(**changes: object) -> ProductSource:
    values: dict[str, object] = {
        "source_type": ProductSourceType.PDF,
        "storage_key": f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/document.pdf",
    }
    values.update(changes)
    return make_product_source(**values)  # type: ignore[arg-type]


def build_service(
    jobs: FakeJobs,
    sources: FakeSources,
    storage: FakeStorage,
    results: FakeResults,
    parser: FakeParser,
) -> PdfTextExtractionService:
    return PdfTextExtractionService(
        cast(ProcessingJobRepository, jobs),
        cast(ProductSourceRepository, sources),
        cast(ObjectStorage, storage),
        cast(PdfExtractionResultRepository, results),
        cast(PdfTextParser, parser),
        clock=lambda: JOB_STARTED_AT,
    )


def standard_parts(
    *,
    pages: tuple[PdfExtractionPage, ...] | None = None,
) -> tuple[FakeJobs, FakeSources, FakeStorage, FakeResults, FakeParser, list[str]]:
    events: list[str] = []
    return (
        FakeJobs(pending_job(), events),
        FakeSources(pdf_source()),
        FakeStorage(events),
        FakeResults(events),
        FakeParser(events, pages or (PdfExtractionPage.create(1, "A" * 30),)),
        events,
    )


def test_success_transitions_and_persists_before_completion() -> None:
    jobs, sources, storage, results, parser, events = standard_parts()
    original_source = sources.source
    result = build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    assert events == [
        "job:RUNNING",
        "storage:open",
        "parser:extract",
        "result:create",
        "job:COMPLETED",
    ]
    assert [job.status for job, _ in jobs.updates] == [
        ProcessingJobStatus.RUNNING,
        ProcessingJobStatus.COMPLETED,
    ]
    running, completed = jobs.updates[0][0], jobs.updates[1][0]
    assert running.started_at == JOB_STARTED_AT
    assert completed.completed_at == JOB_STARTED_AT and completed.progress_percent == 100
    assert completed.result_reference == f"extraction-results/{result.extraction_id}"
    assert completed.error_code is completed.error_message is None
    assert jobs.updates[0][1] == 1 and jobs.updates[1][1] == 2
    assert sources.source == original_source
    assert storage.opened == [original_source.storage_key]  # type: ignore[union-attr]
    assert storage.last_stream is not None and storage.last_stream.closed


@pytest.mark.parametrize(
    "job",
    [
        make_processing_job(job_type=ProcessingJobType.SOURCE_PROCESSING),
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
def test_wrong_type_or_non_pending_job_is_rejected_without_start(job: ProcessingJob) -> None:
    events: list[str] = []
    jobs = FakeJobs(job, events)
    with pytest.raises(InvalidPdfExtractionJobError):
        build_service(
            jobs,
            FakeSources(pdf_source()),
            FakeStorage(events),
            FakeResults(events),
            FakeParser(events, (PdfExtractionPage.create(1, "text"),)),
        ).extract_for_job(job_id=JOB_ID)
    assert jobs.updates == [] and events == []


def test_missing_job_is_rejected_without_other_calls() -> None:
    events: list[str] = []
    sources = FakeSources(pdf_source())
    with pytest.raises(InvalidPdfExtractionJobError):
        build_service(
            FakeJobs(None, events),
            sources,
            FakeStorage(events),
            FakeResults(events),
            FakeParser(events, (PdfExtractionPage.create(1, "text"),)),
        ).extract_for_job(job_id=JOB_ID)
    assert sources.calls == [] and events == []


@pytest.mark.parametrize(
    "source",
    [
        None,
        pdf_source(product_id=SECOND_PRODUCT_ID),
        pdf_source(
            source_type=ProductSourceType.IMAGE,
            original_filename="image.png",
            mime_type="image/png",
        ),
        pdf_source(storage_key=None),
    ],
)
def test_invalid_source_is_rejected_before_running(source: ProductSource | None) -> None:
    events: list[str] = []
    jobs = FakeJobs(pending_job(), events)
    with pytest.raises(InvalidPdfSourceError):
        build_service(
            jobs,
            FakeSources(source),
            FakeStorage(events),
            FakeResults(events),
            FakeParser(events, (PdfExtractionPage.create(1, "text"),)),
        ).extract_for_job(job_id=JOB_ID)
    assert jobs.updates == [] and events == []


def test_existing_result_rejects_duplicate_processing_before_running() -> None:
    jobs, sources, storage, results, parser, events = standard_parts()
    results.existing = make_pdf_extraction_result()
    with pytest.raises(InvalidPdfExtractionJobError):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    assert jobs.updates == [] and events == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (PdfParseError(), "PDF_PARSE_FAILED"),
        (PdfExtractionPageLimitExceededError(), "PDF_EXTRACTION_PAGE_LIMIT_EXCEEDED"),
        (PdfExtractionTextLimitExceededError(), "PDF_EXTRACTION_TEXT_LIMIT_EXCEEDED"),
    ],
)
def test_controlled_parser_failures_mark_running_job_failed(
    error: PdfTextExtractionError, code: str
) -> None:
    jobs, sources, storage, results, parser, _ = standard_parts()
    parser.error = error
    with pytest.raises(type(error)):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    failed = jobs.updates[-1][0]
    assert failed.status is ProcessingJobStatus.FAILED
    assert failed.error_code == code and failed.error_message == error.safe_message
    assert failed.completed_at == JOB_STARTED_AT and results.created == []


@pytest.mark.parametrize(
    ("storage_error", "raised", "code"),
    [
        (
            ObjectNotFoundError("private path"),
            PdfExtractionObjectNotFoundError,
            "PDF_OBJECT_NOT_FOUND",
        ),
        (
            ObjectStorageError("private path"),
            PdfExtractionObjectStorageError,
            "PDF_OBJECT_STORAGE_FAILED",
        ),
    ],
)
def test_storage_failures_mark_job_failed_with_safe_metadata(
    storage_error: Exception, raised: type[Exception], code: str
) -> None:
    jobs, sources, storage, results, parser, _ = standard_parts()
    storage.error = storage_error
    with pytest.raises(raised):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    failed = jobs.updates[-1][0]
    assert failed.status is ProcessingJobStatus.FAILED and failed.error_code == code
    assert "private" not in (failed.error_message or "") and results.created == []


def test_result_persistence_failure_marks_job_failed_and_preserves_repository_error() -> None:
    jobs, sources, storage, results, parser, _ = standard_parts()
    results.create_error = PdfExtractionRepositoryError("private table")
    with pytest.raises(PdfExtractionRepositoryError):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    failed = jobs.updates[-1][0]
    assert failed.status is ProcessingJobStatus.FAILED
    assert failed.error_code == "PDF_EXTRACTION_STORAGE_FAILED"
    assert "private table" not in (failed.error_message or "")


def test_completion_failure_preserves_result_and_leaves_consistency_risk() -> None:
    jobs, sources, storage, results, parser, _ = standard_parts()
    jobs.update_errors[2] = ProcessingJobRepositoryError("completion failed")
    with pytest.raises(ProcessingJobRepositoryError):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    assert len(results.created) == 1
    assert jobs.job is not None and jobs.job.status is ProcessingJobStatus.RUNNING


def test_failure_state_update_error_does_not_mask_parser_error() -> None:
    jobs, sources, storage, results, parser, _ = standard_parts()
    jobs.update_errors[2] = ProcessingJobRepositoryError("failure update failed")
    parser.error = PdfParseError()
    with pytest.raises(PdfParseError):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)


@pytest.mark.parametrize(
    ("pages", "quality"),
    [
        ((PdfExtractionPage.create(1, ""),), "NO_TEXT"),
        ((PdfExtractionPage.create(1, "tiny"),), "LOW_TEXT"),
    ],
)
def test_no_text_and_low_text_are_successful(
    pages: tuple[PdfExtractionPage, ...], quality: str
) -> None:
    jobs, sources, storage, results, parser, _ = standard_parts(pages=pages)
    result = build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    assert result.quality_status.value == quality
    assert jobs.updates[-1][0].status is ProcessingJobStatus.COMPLETED


def test_prestart_result_repository_failure_leaves_job_pending() -> None:
    jobs, sources, storage, results, parser, events = standard_parts()
    results.get_error = PdfExtractionRepositoryError("unavailable")
    with pytest.raises(PdfExtractionRepositoryError):
        build_service(jobs, sources, storage, results, parser).extract_for_job(job_id=JOB_ID)
    assert jobs.updates == [] and events == []


def test_service_contains_no_http_boto3_direct_filesystem_or_execution_api_logic() -> None:
    source = inspect.getsource(service_module).lower()
    for forbidden in ("fastapi", "boto3", "pathlib", "localobjectstorage", "subprocess", "os."):
        assert forbidden not in source
