"""Immutable CSV evidence, aggregate, and quality tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.csv_processing import (
    CsvHeaderCell,
    CsvProcessingQualityStatus,
    CsvProcessingResult,
    CsvRow,
)
from tests.fixtures.csv_processing import make_csv_processing_result
from tests.fixtures.processing_jobs import JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID


def test_result_is_immutable_and_aggregates_evidence() -> None:
    result = make_csv_processing_result()
    assert (result.column_count, result.row_count, result.malformed_row_count) == (3, 2, 1)
    assert result.total_cell_count == 6 and result.empty_cell_count == 1
    assert result.quality_status is CsvProcessingQualityStatus.VALID_WITH_WARNINGS
    assert result.warning_codes == ("CSV_ROW_MISSING_COLUMNS",)
    with pytest.raises(FrozenInstanceError):
        result.row_count = 3  # type: ignore[misc]


def test_valid_header_only_result_has_zero_data_counts() -> None:
    result = CsvProcessingResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        encoding="utf-8",
        delimiter=",",
        header=(CsvHeaderCell.create(0, "name"),),
        rows=(),
    )
    assert result.quality_status is CsvProcessingQualityStatus.VALID
    assert result.row_count == result.total_cell_count == result.empty_cell_count == 0


def test_extra_cells_positions_and_counts_are_preserved() -> None:
    row = CsvRow.create(1, ["A", "B", "C", "", "D"], 3)
    assert [cell.column_index for cell in row.extra_cells] == [3, 4]
    assert row.warning_codes == ("CSV_ROW_EXTRA_COLUMNS",)
    result = make_csv_processing_result(rows=(row,))
    assert result.total_cell_count == 5 and result.empty_cell_count == 1


def test_normalization_preserves_leading_zeroes_and_formula_text() -> None:
    row = CsvRow.create(1, [" 00123 ", "=1+1", " A  B\r\nC\x00 "], 3)
    assert [cell.text for cell in row.cells] == ["00123", "=1+1", "A  B\nC"]


def test_row_and_result_invariants_are_validated() -> None:
    row = CsvRow.create(1, ["A"], 2)
    with pytest.raises(ValueError):
        replace(row, is_malformed=False)
    result = make_csv_processing_result()
    with pytest.raises(ValueError):
        replace(result, rows=tuple(reversed(result.rows)))
    with pytest.raises(ValueError):
        replace(result, delimiter=":")


def test_created_timestamp_is_normalized_to_utc() -> None:
    assert make_csv_processing_result().created_at.utcoffset().total_seconds() == 0
