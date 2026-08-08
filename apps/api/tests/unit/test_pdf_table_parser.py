"""PDF table parser, normalization, ordering, and limit tests."""

from io import BytesIO

import pytest

from app.core.exceptions import (
    PdfTableExtractionCellLimitExceededError,
    PdfTableExtractionCellTextLimitExceededError,
    PdfTableExtractionColumnLimitExceededError,
    PdfTableExtractionPageLimitExceededError,
    PdfTableExtractionRowLimitExceededError,
    PdfTableExtractionTableLimitExceededError,
    PdfTableParseError,
)
from app.services.pdf_table_parser import PdfTableExtractionLimits, PdfTableParser
from tests.fixtures.pdf_extraction import make_pdf_bytes
from tests.fixtures.pdf_table_extraction import make_table_pdf_bytes


def parser(**changes: int) -> PdfTableParser:
    values = dict(
        max_pages=10,
        max_tables=10,
        max_rows_per_table=10,
        max_columns_per_table=10,
        max_cells=100,
        max_cell_characters=100,
    )
    values.update(changes)
    return PdfTableParser(PdfTableExtractionLimits(**values))


def test_extracts_single_table_and_preserves_header_blank_cells() -> None:
    pdf = make_table_pdf_bytes([[[["Model", "Pressure"], ["PX-400", ""]]]])
    output = parser().extract_tables(BytesIO(pdf))
    table = output.tables[0]
    assert output.page_count == 1 and table.page_number == table.table_index == 1
    assert (table.row_count, table.column_count, table.cell_count) == (2, 2, 4)
    assert [cell.text for cell in table.rows[0].cells] == ["Model", "Pressure"]
    assert table.rows[1].cells[1].is_empty


def test_preserves_multiple_tables_and_page_order() -> None:
    pdf = make_table_pdf_bytes(
        [
            [[["A", "B"], ["1", "2"]], [["C", "D"], ["3", "4"]]],
            [[["E", "F"], ["5", "6"]]],
        ]
    )
    output = parser().extract_tables(BytesIO(pdf))
    assert [(table.page_number, table.table_index) for table in output.tables] == [
        (1, 1),
        (1, 2),
        (2, 1),
    ]


def test_readable_pdf_without_detectable_tables_succeeds() -> None:
    output = parser().extract_tables(BytesIO(make_pdf_bytes([["plain text"]])))
    assert output.page_count == 1 and output.tables == ()


def test_corrupt_pdf_is_controlled() -> None:
    with pytest.raises(PdfTableParseError):
        parser().extract_tables(BytesIO(b"not pdf"))


@pytest.mark.parametrize(
    ("changes", "pdf", "error"),
    [
        (
            {"max_pages": 1},
            make_table_pdf_bytes([[], []]),
            PdfTableExtractionPageLimitExceededError,
        ),
        (
            {"max_tables": 1},
            make_table_pdf_bytes([[[["A", "B"], ["1", "2"]], [["C", "D"], ["3", "4"]]]]),
            PdfTableExtractionTableLimitExceededError,
        ),
        (
            {"max_rows_per_table": 1},
            make_table_pdf_bytes([[[["A"], ["B"]]]]),
            PdfTableExtractionRowLimitExceededError,
        ),
        (
            {"max_columns_per_table": 1},
            make_table_pdf_bytes([[[["A", "B"]]]]),
            PdfTableExtractionColumnLimitExceededError,
        ),
        (
            {"max_cells": 3},
            make_table_pdf_bytes([[[["A", "B"], ["C", "D"]]]]),
            PdfTableExtractionCellLimitExceededError,
        ),
        (
            {"max_cell_characters": 2},
            make_table_pdf_bytes([[[["long", "B"], ["C", "D"]]]]),
            PdfTableExtractionCellTextLimitExceededError,
        ),
    ],
)
def test_limits_fail_without_truncation(
    changes: dict[str, int], pdf: bytes, error: type[Exception]
) -> None:
    with pytest.raises(error):
        parser(**changes).extract_tables(BytesIO(pdf))


def test_ragged_rows_are_padded_and_cell_text_is_conservative() -> None:
    table = parser()._normalize_candidate([[" A\r\nB\x00 ", "Unit  bar"], ["C"]], 2, 1)
    assert table is not None
    assert table.rows[0].cells[0].text == "A\nB"
    assert table.rows[0].cells[1].text == "Unit  bar"
    assert table.rows[1].cells[1].is_empty


@pytest.mark.parametrize(
    "field",
    [
        "max_pages",
        "max_tables",
        "max_rows_per_table",
        "max_columns_per_table",
        "max_cells",
        "max_cell_characters",
    ],
)
def test_limits_must_be_positive(field: str) -> None:
    values = dict(
        max_pages=1,
        max_tables=1,
        max_rows_per_table=1,
        max_columns_per_table=1,
        max_cells=1,
        max_cell_characters=1,
    )
    values[field] = 0
    with pytest.raises(ValueError):
        PdfTableExtractionLimits(**values)
