"""PDF table-extraction quality enumerations."""

from enum import StrEnum


class PdfTableExtractionQualityStatus(StrEnum):
    TABLES_FOUND = "TABLES_FOUND"
    NO_TABLES = "NO_TABLES"
    PARTIAL = "PARTIAL"
