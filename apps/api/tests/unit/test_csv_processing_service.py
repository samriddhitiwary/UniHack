"""CSV processing orchestration and lifecycle tests."""

import inspect
from dataclasses import replace
from io import BytesIO
from typing import BinaryIO, cast
from uuid import UUID

import pytest

from app.core.exceptions import (
    CsvDelimiterUndeterminedError,
    CsvEmptyFileError,
    CsvEncodingUnsupportedError,
    CsvObjectNotFoundError,
    CsvObjectStorageError,
    CsvProcessingRepositoryError,
    CsvRowLimitExceededError,
    InvalidCsvProcessingJobError,
    InvalidCsvSourceError,
    ObjectNotFoundError,
    ObjectStorageError,
    ProcessingJobRepositoryError,
)
from app.domain.csv_processing import CsvHeaderCell, CsvProcessingResult, CsvRow
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobPage,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_sources import ProductSource, ProductSourcePage, ProductSourceType
from app.repositories.csv_processing import CsvProcessingResultRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_sources import ProductSourceRepository
from app.services import csv_processing as service_module
from app.services.csv_parser import CsvParser, ParsedCsv
from app.services.csv_processing import CsvProcessingService
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage
from tests.fixtures.csv_processing import make_csv_processing_result
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
        self, product_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProductSourcePage:
        raise NotImplementedError

    def delete(self, product_id: UUID, source_id: UUID, expected_version: int) -> None:
        raise NotImplementedError


class FakeStorage:
    def __init__(self, events: list[str], error: Exception | None = None) -> None:
        self.events = events
        self.error = error
        self.opened: list[str] = []
        self.stream: BytesIO | None = None

    def open(self, object_key: str) -> BinaryIO:
        self.events.append("storage:open")
        self.opened.append(object_key)
        if self.error:
            raise self.error
        self.stream = BytesIO(b"csv")
        return self.stream

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
        self, events: list[str], output: ParsedCsv, error: Exception | None = None
    ) -> None:
        self.events = events
        self.output = output
        self.error = error

    def parse(self, stream: BinaryIO) -> ParsedCsv:
        self.events.append("parser:parse")
        assert not stream.closed
        if self.error:
            raise self.error
        return self.output


class FakeResults:
    def __init__(
        self,
        events: list[str],
        existing: CsvProcessingResult | None = None,
        create_error: Exception | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.events = events
        self.existing = existing
        self.create_error = create_error
        self.get_error = get_error
        self.created: list[CsvProcessingResult] = []

    def create(self, result: CsvProcessingResult) -> CsvProcessingResult:
        self.events.append("result:create")
        self.created.append(result)
        if self.create_error:
            raise self.create_error
        self.existing = result
        return result

    def get_by_id(self, processing_id: UUID) -> CsvProcessingResult | None:
        return (
            self.existing
            if self.existing and self.existing.processing_id == processing_id
            else None
        )

    def get_by_job_id(self, job_id: UUID) -> CsvProcessingResult | None:
        if self.get_error:
            raise self.get_error
        return self.existing if self.existing and self.existing.job_id == job_id else None


def pending_job() -> ProcessingJob:
    return make_processing_job(job_type=ProcessingJobType.CSV_PROCESSING)


def csv_source(**changes: object) -> ProductSource:
    values: dict[str, object] = {
        "source_type": ProductSourceType.CSV,
        "original_filename": "data.csv",
        "mime_type": "text/csv",
        "storage_key": f"products/{PRODUCT_ID}/sources/{SOURCE_ID}/data.csv",
    }
    values.update(changes)
    return make_product_source(**values)  # type: ignore[arg-type]


def parsed(*, rows: tuple[CsvRow, ...] | None = None) -> ParsedCsv:
    header = tuple(CsvHeaderCell.create(index, value) for index, value in enumerate(("A", "B")))
    evidence = rows if rows is not None else (CsvRow.create(1, ["1", "2"], 2),)
    return ParsedCsv("utf-8", ",", header, evidence)


Parts = tuple[FakeJobs, FakeSources, FakeStorage, FakeResults, FakeParser, list[str]]


def standard_parts(*, output: ParsedCsv | None = None) -> Parts:
    events: list[str] = []
    return (
        FakeJobs(pending_job(), events),
        FakeSources(csv_source()),
        FakeStorage(events),
        FakeResults(events),
        FakeParser(events, output or parsed()),
        events,
    )


def build(parts: Parts) -> CsvProcessingService:
    jobs, sources, storage, results, parser, _ = parts
    return CsvProcessingService(
        cast(ProcessingJobRepository, jobs),
        cast(ProductSourceRepository, sources),
        cast(ObjectStorage, storage),
        cast(CsvProcessingResultRepository, results),
        cast(CsvParser, parser),
        clock=lambda: JOB_STARTED_AT,
    )


def test_success_persists_before_completion_and_preserves_source() -> None:
    parts = standard_parts()
    jobs, sources, storage, _, _, events = parts
    original = sources.source
    result = build(parts).process_for_job(job_id=JOB_ID)
    assert events == [
        "job:RUNNING",
        "storage:open",
        "parser:parse",
        "result:create",
        "job:COMPLETED",
    ]
    assert jobs.updates[0][0].started_at == JOB_STARTED_AT
    completed = jobs.updates[-1][0]
    assert completed.status is ProcessingJobStatus.COMPLETED
    assert completed.progress_percent == 100 and completed.completed_at == JOB_STARTED_AT
    assert completed.result_reference == f"csv-processing-results/{result.processing_id}"
    assert completed.error_code is completed.error_message is None
    assert sources.source == original and storage.stream is not None and storage.stream.closed


@pytest.mark.parametrize(
    "job",
    [
        make_processing_job(job_type=ProcessingJobType.PDF_TABLE_EXTRACTION),
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
def test_wrong_type_or_non_pending_job_is_rejected(job: ProcessingJob) -> None:
    parts = standard_parts()
    parts[0].job = job
    with pytest.raises(InvalidCsvProcessingJobError):
        build(parts).process_for_job(job_id=JOB_ID)
    assert parts[0].updates == [] and parts[-1] == []


def test_missing_job_is_rejected_before_source_lookup() -> None:
    parts = standard_parts()
    parts[0].job = None
    with pytest.raises(InvalidCsvProcessingJobError):
        build(parts).process_for_job(job_id=JOB_ID)
    assert parts[1].calls == []


@pytest.mark.parametrize(
    "source",
    [
        None,
        csv_source(product_id=SECOND_PRODUCT_ID),
        csv_source(
            source_type=ProductSourceType.PDF,
            original_filename="x.pdf",
            mime_type="application/pdf",
        ),
        csv_source(storage_key=None),
    ],
)
def test_invalid_source_is_rejected_before_running(source: ProductSource | None) -> None:
    parts = standard_parts()
    parts[1].source = source
    with pytest.raises(InvalidCsvSourceError):
        build(parts).process_for_job(job_id=JOB_ID)
    assert parts[0].updates == []


def test_existing_result_and_lookup_failure_do_not_start() -> None:
    parts = standard_parts()
    parts[3].existing = make_csv_processing_result()
    with pytest.raises(InvalidCsvProcessingJobError):
        build(parts).process_for_job(job_id=JOB_ID)
    parts = standard_parts()
    parts[3].get_error = CsvProcessingRepositoryError("private")
    with pytest.raises(CsvProcessingRepositoryError):
        build(parts).process_for_job(job_id=JOB_ID)
    assert parts[0].updates == []


@pytest.mark.parametrize(
    "error",
    [
        CsvEmptyFileError(),
        CsvEncodingUnsupportedError(),
        CsvDelimiterUndeterminedError(),
        CsvRowLimitExceededError(),
    ],
)
def test_controlled_parser_failures_mark_job_failed(error: Exception) -> None:
    parts = standard_parts()
    parts[4].error = error
    with pytest.raises(type(error)):
        build(parts).process_for_job(job_id=JOB_ID)
    failed = parts[0].updates[-1][0]
    assert failed.status is ProcessingJobStatus.FAILED
    assert failed.error_code == error.code  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("failure", "raised", "code"),
    [
        (ObjectNotFoundError("private"), CsvObjectNotFoundError, "CSV_OBJECT_NOT_FOUND"),
        (ObjectStorageError("private"), CsvObjectStorageError, "CSV_OBJECT_STORAGE_FAILED"),
    ],
)
def test_storage_failures_store_safe_metadata(
    failure: Exception, raised: type[Exception], code: str
) -> None:
    parts = standard_parts()
    parts[2].error = failure
    with pytest.raises(raised):
        build(parts).process_for_job(job_id=JOB_ID)
    failed = parts[0].updates[-1][0]
    assert failed.error_code == code and "private" not in (failed.error_message or "")


def test_persistence_failure_marks_failed_and_preserves_repository_error() -> None:
    parts = standard_parts()
    parts[3].create_error = CsvProcessingRepositoryError("private")
    with pytest.raises(CsvProcessingRepositoryError):
        build(parts).process_for_job(job_id=JOB_ID)
    assert parts[0].updates[-1][0].error_code == "CSV_PROCESSING_STORAGE_FAILED"


def test_completion_failure_preserves_result_and_logs_risk(
    caplog: pytest.LogCaptureFixture,
) -> None:
    parts = standard_parts()
    parts[0].update_errors[2] = ProcessingJobRepositoryError("failed")
    with pytest.raises(ProcessingJobRepositoryError):
        build(parts).process_for_job(job_id=JOB_ID)
    assert len(parts[3].created) == 1 and parts[0].job is not None
    assert parts[0].job.status is ProcessingJobStatus.RUNNING
    assert "csv_processing.completion_consistency_risk" in caplog.text


@pytest.mark.parametrize(
    "rows",
    [(), (CsvRow.create(1, ["only"], 2),), (CsvRow.create(1, ["1", "2", "3"], 2),)],
)
def test_header_only_and_recoverable_rows_complete(rows: tuple[CsvRow, ...]) -> None:
    parts = standard_parts(output=parsed(rows=rows))
    result = build(parts).process_for_job(job_id=JOB_ID)
    assert parts[0].updates[-1][0].status is ProcessingJobStatus.COMPLETED
    assert result.quality_status.value == ("VALID" if not rows else "VALID_WITH_WARNINGS")


def test_failure_update_does_not_mask_processing_error() -> None:
    parts = standard_parts()
    parts[0].update_errors[2] = ProcessingJobRepositoryError("failed")
    parts[4].error = CsvEmptyFileError()
    with pytest.raises(CsvEmptyFileError):
        build(parts).process_for_job(job_id=JOB_ID)


def test_service_has_no_http_boto3_filesystem_or_execution_api_logic() -> None:
    source = inspect.getsource(service_module).lower()
    for forbidden in ("fastapi", "boto3", "pathlib", "localobjectstorage", "subprocess", "os."):
        assert forbidden not in source
