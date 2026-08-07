"""PDF text-extraction quality enumerations."""

from enum import StrEnum


class PdfExtractionQualityStatus(StrEnum):
    USABLE = "USABLE"
    LOW_TEXT = "LOW_TEXT"
    NO_TEXT = "NO_TEXT"
