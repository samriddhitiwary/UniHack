"""Structured attribute extraction enumerations."""

from enum import StrEnum


class AttributeExtractionEvidenceType(StrEnum):
    DIRECT_TEXT = "DIRECT_TEXT"
    PDF_TEXT = "PDF_TEXT"
    PDF_TABLE_ROW = "PDF_TABLE_ROW"
    PDF_TABLE_CELL = "PDF_TABLE_CELL"
    CSV_ROW = "CSV_ROW"
    CSV_CELL = "CSV_CELL"
    IMAGE_OCR = "IMAGE_OCR"


class AttributeMatchType(StrEnum):
    EXACT = "EXACT"
    NORMALIZED = "NORMALIZED"
    CONTEXTUAL = "CONTEXTUAL"


class AttributeValueParseStatus(StrEnum):
    PARSED = "PARSED"
    RAW_TEXT = "RAW_TEXT"
    MISSING_VALUE = "MISSING_VALUE"


class StructuredAttributeExtractionStatus(StrEnum):
    CANDIDATES_FOUND = "CANDIDATES_FOUND"
    NO_CANDIDATES = "NO_CANDIDATES"
    CANDIDATES_WITH_WARNINGS = "CANDIDATES_WITH_WARNINGS"
