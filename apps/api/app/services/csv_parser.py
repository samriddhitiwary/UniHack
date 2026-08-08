"""Bounded standard-library CSV parsing and evidence preservation."""

import codecs
import csv
from dataclasses import dataclass
from io import StringIO
from typing import BinaryIO

from app.core.exceptions import (
    CsvCellLimitExceededError,
    CsvCellTextLimitExceededError,
    CsvColumnLimitExceededError,
    CsvDelimiterUndeterminedError,
    CsvEmptyFileError,
    CsvEncodingUnsupportedError,
    CsvFileSizeLimitExceededError,
    CsvParseError,
    CsvProcessingError,
    CsvRowLimitExceededError,
)
from app.domain.csv_processing import CsvHeaderCell, CsvRow, normalize_csv_cell

ENCODING = "utf-8"
ALLOWED_DELIMITERS = (",", ";", "\t", "|")
READ_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class CsvProcessingLimits:
    max_file_bytes: int = 5 * 1024 * 1024
    max_rows: int = 100_000
    max_columns: int = 500
    max_total_cells: int = 1_000_000
    max_cell_characters: int = 50_000
    sample_bytes: int = 65_536

    def __post_init__(self) -> None:
        for name, value in (
            ("max_file_bytes", self.max_file_bytes),
            ("max_rows", self.max_rows),
            ("max_columns", self.max_columns),
            ("max_total_cells", self.max_total_cells),
            ("max_cell_characters", self.max_cell_characters),
            ("sample_bytes", self.sample_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class ParsedCsv:
    encoding: str
    delimiter: str
    header: tuple[CsvHeaderCell, ...]
    rows: tuple[CsvRow, ...]


class CsvParser:
    def __init__(self, limits: CsvProcessingLimits) -> None:
        self._limits = limits

    def parse(self, stream: BinaryIO) -> ParsedCsv:
        raw = self._read_bounded(stream)
        try:
            text = raw.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise CsvEncodingUnsupportedError() from exc
        if not text or not text.replace("\r", "").replace("\n", ""):
            raise CsvEmptyFileError()
        delimiter = self._detect_delimiter(raw, text)
        try:
            parsed_rows = csv.reader(StringIO(text, newline=""), delimiter=delimiter, strict=True)
            meaningful = (row for row in parsed_rows if row != [])
            raw_header = next(meaningful, None)
            if raw_header is None:
                raise CsvEmptyFileError()
            header = self._create_header(raw_header)
            rows: list[CsvRow] = []
            total_cells = 0
            for raw_row in meaningful:
                if len(rows) + 1 > self._limits.max_rows:
                    raise CsvRowLimitExceededError()
                if len(raw_row) > self._limits.max_columns:
                    raise CsvColumnLimitExceededError()
                self._validate_cell_text(raw_row)
                row = CsvRow.create(len(rows) + 1, raw_row, len(header))
                total_cells += len(row.cells) + len(row.extra_cells)
                if total_cells > self._limits.max_total_cells:
                    raise CsvCellLimitExceededError()
                rows.append(row)
        except CsvProcessingError:
            raise
        except csv.Error as exc:
            raise CsvParseError() from exc
        except Exception as exc:
            raise CsvParseError() from exc
        return ParsedCsv(ENCODING, delimiter, header, tuple(rows))

    def _read_bounded(self, stream: BinaryIO) -> bytes:
        parts: list[bytes] = []
        total = 0
        while True:
            chunk = stream.read(min(READ_CHUNK_BYTES, self._limits.max_file_bytes + 1 - total))
            if not chunk:
                return b"".join(parts)
            if not isinstance(chunk, bytes):
                raise CsvParseError()
            parts.append(chunk)
            total += len(chunk)
            if total > self._limits.max_file_bytes:
                raise CsvFileSizeLimitExceededError()

    def _detect_delimiter(self, raw: bytes, text: str) -> str:
        decoder = codecs.getincrementaldecoder("utf-8-sig")()
        sample = decoder.decode(raw[: self._limits.sample_bytes], final=False)
        try:
            delimiter = (
                csv.Sniffer().sniff(sample, delimiters="".join(ALLOWED_DELIMITERS)).delimiter
            )
        except csv.Error:
            delimiter = "," if _has_unquoted_comma(sample) else ""
        if delimiter not in ALLOWED_DELIMITERS:
            raise CsvDelimiterUndeterminedError()
        return delimiter

    def _create_header(self, raw_header: list[str]) -> tuple[CsvHeaderCell, ...]:
        if not raw_header:
            raise CsvEmptyFileError()
        if len(raw_header) > self._limits.max_columns:
            raise CsvColumnLimitExceededError()
        self._validate_cell_text(raw_header)
        return tuple(CsvHeaderCell.create(index, value) for index, value in enumerate(raw_header))

    def _validate_cell_text(self, values: list[str]) -> None:
        if any(
            len(normalize_csv_cell(value)) > self._limits.max_cell_characters for value in values
        ):
            raise CsvCellTextLimitExceededError()


def _has_unquoted_comma(sample: str) -> bool:
    quoted = False
    index = 0
    while index < len(sample):
        character = sample[index]
        if character == '"':
            if quoted and index + 1 < len(sample) and sample[index + 1] == '"':
                index += 1
            else:
                quoted = not quoted
        elif character == "," and not quoted:
            return True
        index += 1
    return False
