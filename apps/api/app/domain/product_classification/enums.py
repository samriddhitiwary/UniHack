"""Product-classification enumerations."""

from enum import IntEnum, StrEnum


class ClassificationEvidenceType(StrEnum):
    DIRECT_TEXT = "DIRECT_TEXT"
    PDF_TEXT = "PDF_TEXT"
    PDF_TABLE_CELL = "PDF_TABLE_CELL"
    CSV_HEADER = "CSV_HEADER"
    CSV_CELL = "CSV_CELL"
    IMAGE_OCR = "IMAGE_OCR"


class ClassificationSignalStrength(IntEnum):
    WEAK = 1
    MEDIUM = 4
    STRONG = 10


class ProductClassificationStatus(StrEnum):
    CLASSIFIED = "CLASSIFIED"
    AMBIGUOUS = "AMBIGUOUS"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
