"""Deterministic CSV processing fixtures."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.csv_processing import CsvHeaderCell, CsvProcessingResult, CsvRow
from tests.fixtures.processing_jobs import JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

PROCESSING_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")
PROCESSING_CREATED_AT = datetime(2026, 8, 8, 7, 0, tzinfo=UTC)


def make_csv_processing_result(
    *,
    processing_id: UUID = PROCESSING_ID,
    rows: tuple[CsvRow, ...] | None = None,
) -> CsvProcessingResult:
    header = tuple(
        CsvHeaderCell.create(index, text)
        for index, text in enumerate(("manufacturer", "model", "power"))
    )
    evidence = (
        rows
        if rows is not None
        else (
            CsvRow.create(1, ["ABC", "00123", "5 kW"], len(header)),
            CsvRow.create(2, ["XYZ", "PX-2"], len(header)),
        )
    )
    created = CsvProcessingResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        encoding="utf-8",
        delimiter=",",
        header=header,
        rows=evidence,
        now=PROCESSING_CREATED_AT,
    )
    return CsvProcessingResult(
        processing_id=processing_id,
        job_id=created.job_id,
        product_id=created.product_id,
        source_id=created.source_id,
        encoding=created.encoding,
        delimiter=created.delimiter,
        header=created.header,
        column_count=created.column_count,
        row_count=created.row_count,
        malformed_row_count=created.malformed_row_count,
        empty_cell_count=created.empty_cell_count,
        total_cell_count=created.total_cell_count,
        quality_status=created.quality_status,
        rows=created.rows,
        warning_codes=created.warning_codes,
        created_at=created.created_at,
    )
