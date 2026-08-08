"""Bounded page-level PDF table extraction using pdfplumber."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, BinaryIO, cast

import pdfplumber

from app.core.exceptions import (
    PdfTableExtractionCellLimitExceededError,
    PdfTableExtractionCellTextLimitExceededError,
    PdfTableExtractionColumnLimitExceededError,
    PdfTableExtractionError,
    PdfTableExtractionPageLimitExceededError,
    PdfTableExtractionRowLimitExceededError,
    PdfTableExtractionTableLimitExceededError,
    PdfTableParseError,
)
from app.domain.pdf_table_extraction import PdfExtractedTable, PdfTableCell, PdfTableRow

PARSER_NAME = "pdfplumber"
PARSER_VERSION = pdfplumber.__version__


@dataclass(frozen=True, slots=True)
class PdfTableExtractionLimits:
    max_pages: int = 300
    max_tables: int = 500
    max_rows_per_table: int = 5_000
    max_columns_per_table: int = 200
    max_cells: int = 500_000
    max_cell_characters: int = 20_000

    def __post_init__(self) -> None:
        for name, value in (
            ("max_pages", self.max_pages),
            ("max_tables", self.max_tables),
            ("max_rows_per_table", self.max_rows_per_table),
            ("max_columns_per_table", self.max_columns_per_table),
            ("max_cells", self.max_cells),
            ("max_cell_characters", self.max_cell_characters),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class PdfTableParseOutput:
    page_count: int
    tables: tuple[PdfExtractedTable, ...]
    warning_codes: tuple[str, ...] = ()


class PdfTableParser:
    def __init__(self, limits: PdfTableExtractionLimits) -> None:
        self._limits = limits

    def extract_tables(self, stream: BinaryIO) -> PdfTableParseOutput:
        tables: list[PdfExtractedTable] = []
        total_cells = 0
        try:
            with pdfplumber.open(cast(Any, stream)) as pdf:
                page_count = len(pdf.pages)
                if page_count < 1:
                    raise PdfTableParseError()
                if page_count > self._limits.max_pages:
                    raise PdfTableExtractionPageLimitExceededError()
                for page_number, page in enumerate(pdf.pages, start=1):
                    candidates = page.extract_tables()
                    page_table_index = 0
                    for candidate in candidates:
                        normalized = self._normalize_candidate(
                            candidate, page_number, page_table_index + 1
                        )
                        if normalized is None:
                            continue
                        page_table_index += 1
                        if len(tables) + 1 > self._limits.max_tables:
                            raise PdfTableExtractionTableLimitExceededError()
                        total_cells += normalized.cell_count
                        if total_cells > self._limits.max_cells:
                            raise PdfTableExtractionCellLimitExceededError()
                        tables.append(normalized)
        except PdfTableExtractionError:
            raise
        except Exception as exc:
            raise PdfTableParseError() from exc
        return PdfTableParseOutput(page_count, tuple(tables))

    def _normalize_candidate(
        self,
        candidate: Sequence[Sequence[str | None] | None],
        page_number: int,
        table_index: int,
    ) -> PdfExtractedTable | None:
        if len(candidate) > self._limits.max_rows_per_table:
            raise PdfTableExtractionRowLimitExceededError()
        column_count = max((len(row) if row is not None else 0 for row in candidate), default=0)
        if column_count == 0:
            return None
        if column_count > self._limits.max_columns_per_table:
            raise PdfTableExtractionColumnLimitExceededError()
        rows: list[PdfTableRow] = []
        for row_index, raw_row in enumerate(candidate):
            values = list(raw_row or ())
            values.extend([None] * (column_count - len(values)))
            cells = tuple(
                PdfTableCell.create(row_index, column_index, value)
                for column_index, value in enumerate(values)
            )
            if any(len(cell.text) > self._limits.max_cell_characters for cell in cells):
                raise PdfTableExtractionCellTextLimitExceededError()
            rows.append(PdfTableRow(row_index, cells))
        if not rows or all(cell.is_empty for row in rows for cell in row.cells):
            return None
        return PdfExtractedTable(
            table_index=table_index,
            page_number=page_number,
            row_count=len(rows),
            column_count=column_count,
            cell_count=len(rows) * column_count,
            rows=tuple(rows),
        )
