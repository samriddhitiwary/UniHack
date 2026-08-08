"""Immutable PDF table evidence and quality tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.pdf_table_extraction import (
    PdfTableCell,
    PdfTableExtractionQualityStatus,
    PdfTableExtractionResult,
    PdfTableRow,
)
from tests.fixtures.pdf_table_extraction import make_pdf_table_extraction_result, make_table
from tests.fixtures.processing_jobs import JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID


def test_models_are_immutable_and_aggregate_counts_are_derived() -> None:
    result = make_pdf_table_extraction_result()
    assert (result.page_count, result.pages_with_tables, result.table_count) == (2, 2, 2)
    assert result.total_row_count == 4 and result.total_cell_count == 8
    assert result.quality_status is PdfTableExtractionQualityStatus.TABLES_FOUND
    with pytest.raises(FrozenInstanceError):
        result.table_count = 3  # type: ignore[misc]


def test_no_tables_is_valid_success_quality() -> None:
    result = PdfTableExtractionResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        parser="pdfplumber",
        parser_version="1",
        page_count=1,
        tables=(),
    )
    assert result.quality_status is PdfTableExtractionQualityStatus.NO_TABLES


def test_real_warning_with_tables_is_partial() -> None:
    result = PdfTableExtractionResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        parser="parser",
        parser_version="1",
        page_count=1,
        tables=(make_table(),),
        warning_codes=("PAGE_DEGRADED",),
    )
    assert result.quality_status is PdfTableExtractionQualityStatus.PARTIAL


def test_invalid_cell_empty_flag_is_rejected() -> None:
    valid = PdfTableCell.create(0, 0, "value")
    with pytest.raises(ValueError):
        replace(valid, is_empty=True)


def test_row_positions_and_table_order_are_validated() -> None:
    with pytest.raises(ValueError):
        PdfTableRow(0, (PdfTableCell.create(0, 1, "x"),))
    result = make_pdf_table_extraction_result()
    with pytest.raises(ValueError):
        replace(result, tables=tuple(reversed(result.tables)))


def test_all_empty_table_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_table(values=((None, ""),))
