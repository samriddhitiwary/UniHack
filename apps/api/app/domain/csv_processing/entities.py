"""Immutable CSV header, row, cell, and result evidence."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from app.domain.csv_processing.enums import CsvProcessingQualityStatus

ENCODING_MAX_LENGTH = 20
WARNING_CODE_MAX_LENGTH = 100
MISSING_COLUMNS_WARNING = "CSV_ROW_MISSING_COLUMNS"
EXTRA_COLUMNS_WARNING = "CSV_ROW_EXTRA_COLUMNS"


def normalize_csv_cell(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("CSV cell text must be a string")
    return value.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _index(value: int, field: str, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} must be an integer of at least {minimum}")


@dataclass(frozen=True, slots=True)
class CsvHeaderCell:
    column_index: int
    text: str
    is_empty: bool

    def __post_init__(self) -> None:
        _index(self.column_index, "column_index", minimum=0)
        if self.text != normalize_csv_cell(self.text):
            raise ValueError("header text must be conservatively normalized")
        if self.is_empty is not (self.text == ""):
            raise ValueError("is_empty must match header text")

    @classmethod
    def create(cls, column_index: int, raw_text: str) -> Self:
        text = normalize_csv_cell(raw_text)
        return cls(column_index, text, text == "")


@dataclass(frozen=True, slots=True)
class CsvCell:
    column_index: int
    text: str
    is_empty: bool

    def __post_init__(self) -> None:
        _index(self.column_index, "column_index", minimum=0)
        if self.text != normalize_csv_cell(self.text):
            raise ValueError("cell text must be conservatively normalized")
        if self.is_empty is not (self.text == ""):
            raise ValueError("is_empty must match cell text")

    @classmethod
    def create(cls, column_index: int, raw_text: str) -> Self:
        text = normalize_csv_cell(raw_text)
        return cls(column_index, text, text == "")


@dataclass(frozen=True, slots=True, kw_only=True)
class CsvRow:
    row_number: int
    cells: tuple[CsvCell, ...]
    extra_cells: tuple[CsvCell, ...]
    original_column_count: int
    normalized_column_count: int
    is_malformed: bool
    warning_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _index(self.row_number, "row_number", minimum=1)
        _index(self.original_column_count, "original_column_count", minimum=0)
        _index(self.normalized_column_count, "normalized_column_count", minimum=1)
        if len(self.cells) != self.normalized_column_count:
            raise ValueError("regular cells must match normalized column count")
        if tuple(cell.column_index for cell in self.cells) != tuple(
            range(self.normalized_column_count)
        ):
            raise ValueError("regular cells must have consecutive zero-based indices")
        expected_extra = max(0, self.original_column_count - self.normalized_column_count)
        if len(self.extra_cells) != expected_extra:
            raise ValueError("extra cells must preserve every overflow column")
        if tuple(cell.column_index for cell in self.extra_cells) != tuple(
            range(self.normalized_column_count, self.original_column_count)
        ):
            raise ValueError("extra cell indices must continue after regular cells")
        expected_warning: tuple[str, ...] = ()
        if self.original_column_count < self.normalized_column_count:
            expected_warning = (MISSING_COLUMNS_WARNING,)
        elif self.original_column_count > self.normalized_column_count:
            expected_warning = (EXTRA_COLUMNS_WARNING,)
        if self.warning_codes != expected_warning or self.is_malformed is not bool(
            expected_warning
        ):
            raise ValueError("malformed state and warnings must match row width")

    @classmethod
    def create(cls, row_number: int, raw_values: list[str], column_count: int) -> Self:
        _index(column_count, "column_count", minimum=1)
        original = len(raw_values)
        regular = raw_values[:column_count] + [""] * max(0, column_count - original)
        extra = raw_values[column_count:]
        warning_codes: tuple[str, ...] = ()
        if original < column_count:
            warning_codes = (MISSING_COLUMNS_WARNING,)
        elif original > column_count:
            warning_codes = (EXTRA_COLUMNS_WARNING,)
        return cls(
            row_number=row_number,
            cells=tuple(CsvCell.create(index, value) for index, value in enumerate(regular)),
            extra_cells=tuple(
                CsvCell.create(column_count + index, value) for index, value in enumerate(extra)
            ),
            original_column_count=original,
            normalized_column_count=column_count,
            is_malformed=bool(warning_codes),
            warning_codes=warning_codes,
        )


def assess_csv_quality(rows: tuple[CsvRow, ...]) -> CsvProcessingQualityStatus:
    if any(row.is_malformed for row in rows):
        return CsvProcessingQualityStatus.VALID_WITH_WARNINGS
    return CsvProcessingQualityStatus.VALID


@dataclass(frozen=True, slots=True, kw_only=True)
class CsvProcessingResult:
    processing_id: UUID
    job_id: UUID
    product_id: UUID
    source_id: UUID
    encoding: str
    delimiter: str
    header: tuple[CsvHeaderCell, ...]
    column_count: int
    row_count: int
    malformed_row_count: int
    empty_cell_count: int
    total_cell_count: int
    quality_status: CsvProcessingQualityStatus
    rows: tuple[CsvRow, ...]
    warning_codes: tuple[str, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (self.processing_id, self.job_id, self.product_id, self.source_id)
        ):
            raise ValueError("result identities must be UUIDs")
        if not self.encoding.strip() or len(self.encoding) > ENCODING_MAX_LENGTH:
            raise ValueError("encoding must be nonempty and bounded")
        if self.delimiter not in {",", ";", "\t", "|"}:
            raise ValueError("delimiter must be allowlisted")
        if not self.header or self.column_count != len(self.header):
            raise ValueError("column_count must match a nonempty header")
        if tuple(cell.column_index for cell in self.header) != tuple(range(self.column_count)):
            raise ValueError("header cells must have consecutive zero-based indices")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows")
        if tuple(row.row_number for row in self.rows) != tuple(range(1, self.row_count + 1)):
            raise ValueError("rows must be ordered and numbered from one")
        if any(row.normalized_column_count != self.column_count for row in self.rows):
            raise ValueError("every row must use the header width")
        if self.malformed_row_count != sum(row.is_malformed for row in self.rows):
            raise ValueError("malformed_row_count must match rows")
        all_cells = tuple(cell for row in self.rows for cell in row.cells + row.extra_cells)
        if self.empty_cell_count != sum(cell.is_empty for cell in all_cells):
            raise ValueError("empty_cell_count must match row evidence")
        if self.total_cell_count != len(all_cells):
            raise ValueError("total_cell_count must match row evidence")
        expected_warnings = tuple(
            dict.fromkeys(code for row in self.rows for code in row.warning_codes)
        )
        if self.warning_codes != expected_warnings or any(
            not code.strip() or len(code) > WARNING_CODE_MAX_LENGTH for code in self.warning_codes
        ):
            raise ValueError("result warnings must be the ordered union of row warnings")
        if self.quality_status is not assess_csv_quality(self.rows):
            raise ValueError("quality_status must match row evidence")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "encoding", self.encoding.strip().lower())
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        source_id: UUID,
        encoding: str,
        delimiter: str,
        header: tuple[CsvHeaderCell, ...],
        rows: tuple[CsvRow, ...],
        now: datetime | None = None,
    ) -> Self:
        cells = tuple(cell for row in rows for cell in row.cells + row.extra_cells)
        warnings = tuple(dict.fromkeys(code for row in rows for code in row.warning_codes))
        return cls(
            processing_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            source_id=source_id,
            encoding=encoding,
            delimiter=delimiter,
            header=header,
            column_count=len(header),
            row_count=len(rows),
            malformed_row_count=sum(row.is_malformed for row in rows),
            empty_cell_count=sum(cell.is_empty for cell in cells),
            total_cell_count=len(cells),
            quality_status=assess_csv_quality(rows),
            rows=rows,
            warning_codes=warnings,
            created_at=now or datetime.now(UTC),
        )
