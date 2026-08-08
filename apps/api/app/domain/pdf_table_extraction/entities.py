"""Immutable, ordered PDF table evidence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.pdf_table_extraction.enums import PdfTableExtractionQualityStatus

PARSER_NAME_MAX_LENGTH = 50
PARSER_VERSION_MAX_LENGTH = 50
WARNING_CODE_MAX_LENGTH = 100


def normalize_pdf_table_cell(value: str | None) -> str:
    """Normalize parser text without changing its meaning."""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError("PDF table cell text must be a string or null")
    return value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


@dataclass(frozen=True, slots=True)
class PdfTableCell:
    row_index: int
    column_index: int
    text: str
    is_empty: bool

    def __post_init__(self) -> None:
        if (
            isinstance(self.row_index, bool)
            or not isinstance(self.row_index, int)
            or self.row_index < 0
        ):
            raise ValueError("row_index must be a non-negative integer")
        if (
            isinstance(self.column_index, bool)
            or not isinstance(self.column_index, int)
            or self.column_index < 0
        ):
            raise ValueError("column_index must be a non-negative integer")
        if self.text != normalize_pdf_table_cell(self.text):
            raise ValueError("cell text must be conservatively normalized")
        if self.is_empty is not (self.text == ""):
            raise ValueError("is_empty must match cell text")

    @classmethod
    def create(cls, row_index: int, column_index: int, raw_text: str | None) -> Self:
        text = normalize_pdf_table_cell(raw_text)
        return cls(row_index, column_index, text, text == "")


@dataclass(frozen=True, slots=True)
class PdfTableRow:
    row_index: int
    cells: tuple[PdfTableCell, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.row_index, bool)
            or not isinstance(self.row_index, int)
            or self.row_index < 0
        ):
            raise ValueError("row_index must be a non-negative integer")
        if not self.cells:
            raise ValueError("a normalized row must contain cells")
        if tuple(cell.row_index for cell in self.cells) != (self.row_index,) * len(self.cells):
            raise ValueError("cell row indices must match their row")
        if tuple(cell.column_index for cell in self.cells) != tuple(range(len(self.cells))):
            raise ValueError("cells must have consecutive zero-based column indices")


@dataclass(frozen=True, slots=True, kw_only=True)
class PdfExtractedTable:
    table_index: int
    page_number: int
    row_count: int
    column_count: int
    cell_count: int
    rows: tuple[PdfTableRow, ...]

    def __post_init__(self) -> None:
        if self.table_index < 1 or self.page_number < 1:
            raise ValueError("page_number and table_index must be positive")
        if not self.rows or self.row_count != len(self.rows):
            raise ValueError("row_count must match non-empty row evidence")
        if tuple(row.row_index for row in self.rows) != tuple(range(self.row_count)):
            raise ValueError("rows must have consecutive zero-based indices")
        widths = {len(row.cells) for row in self.rows}
        if len(widths) != 1 or self.column_count != next(iter(widths)) or self.column_count < 1:
            raise ValueError("rows must form the declared rectangular table")
        if self.cell_count != self.row_count * self.column_count:
            raise ValueError("cell_count must match normalized dimensions")
        if all(cell.is_empty for row in self.rows for cell in row.cells):
            raise ValueError("all-empty tables are parser noise")


def assess_pdf_table_quality(
    tables: tuple[PdfExtractedTable, ...], warning_codes: tuple[str, ...]
) -> PdfTableExtractionQualityStatus:
    if not tables:
        return PdfTableExtractionQualityStatus.NO_TABLES
    if warning_codes:
        return PdfTableExtractionQualityStatus.PARTIAL
    return PdfTableExtractionQualityStatus.TABLES_FOUND


@dataclass(frozen=True, slots=True, kw_only=True)
class PdfTableExtractionResult:
    extraction_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    parser: str
    parser_version: str
    page_count: int
    pages_with_tables: int
    table_count: int
    total_row_count: int
    total_cell_count: int
    quality_status: PdfTableExtractionQualityStatus
    tables: tuple[PdfExtractedTable, ...]
    warning_codes: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (self.extraction_id, self.job_id, self.product_id, self.source_id)
        ):
            raise ValueError("result identities must be UUIDs")
        if not self.parser.strip() or len(self.parser) > PARSER_NAME_MAX_LENGTH:
            raise ValueError("parser must be nonempty and bounded")
        if not self.parser_version.strip() or len(self.parser_version) > PARSER_VERSION_MAX_LENGTH:
            raise ValueError("parser_version must be nonempty and bounded")
        if (
            isinstance(self.page_count, bool)
            or not isinstance(self.page_count, int)
            or self.page_count < 1
        ):
            raise ValueError("page_count must be positive")
        ordering = tuple((table.page_number, table.table_index) for table in self.tables)
        if ordering != tuple(sorted(ordering)) or len(ordering) != len(set(ordering)):
            raise ValueError("tables must have unique page-ordered identities")
        for page in {table.page_number for table in self.tables}:
            indices = tuple(table.table_index for table in self.tables if table.page_number == page)
            if indices != tuple(range(1, len(indices) + 1)):
                raise ValueError("table indices must restart at one on each page")
        if self.tables and max(table.page_number for table in self.tables) > self.page_count:
            raise ValueError("table page cannot exceed page_count")
        if self.pages_with_tables != len({table.page_number for table in self.tables}):
            raise ValueError("pages_with_tables must match table evidence")
        if self.table_count != len(self.tables):
            raise ValueError("table_count must match table evidence")
        if self.total_row_count != sum(table.row_count for table in self.tables):
            raise ValueError("total_row_count must match table evidence")
        if self.total_cell_count != sum(table.cell_count for table in self.tables):
            raise ValueError("total_cell_count must match table evidence")
        if len(set(self.warning_codes)) != len(self.warning_codes) or any(
            not code.strip() or len(code) > WARNING_CODE_MAX_LENGTH for code in self.warning_codes
        ):
            raise ValueError("warning codes must be unique, nonempty, and bounded")
        if not self.tables and self.warning_codes:
            raise ValueError("NO_TABLES results cannot carry partial warnings")
        if self.quality_status is not assess_pdf_table_quality(self.tables, self.warning_codes):
            raise ValueError("quality_status must match table evidence and warnings")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "parser", self.parser.strip())
        object.__setattr__(self, "parser_version", self.parser_version.strip())
        object.__setattr__(
            self, "warning_codes", tuple(code.strip() for code in self.warning_codes)
        )
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        source_id: UUID,
        parser: str,
        parser_version: str,
        page_count: int,
        tables: tuple[PdfExtractedTable, ...],
        warning_codes: tuple[str, ...] = (),
        now: datetime | None = None,
    ) -> Self:
        return cls(
            extraction_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            source_id=source_id,
            parser=parser,
            parser_version=parser_version,
            page_count=page_count,
            pages_with_tables=len({table.page_number for table in tables}),
            table_count=len(tables),
            total_row_count=sum(table.row_count for table in tables),
            total_cell_count=sum(table.cell_count for table in tables),
            quality_status=assess_pdf_table_quality(tables, warning_codes),
            tables=tables,
            warning_codes=warning_codes,
            created_at=now or datetime.now(UTC),
        )
