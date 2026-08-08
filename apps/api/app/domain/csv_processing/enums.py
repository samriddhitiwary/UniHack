"""CSV processing quality enumerations."""

from enum import StrEnum


class CsvProcessingQualityStatus(StrEnum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
