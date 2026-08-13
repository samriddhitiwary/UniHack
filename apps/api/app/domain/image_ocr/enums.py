"""Image OCR evidence and deterministic assessment enumerations."""

from enum import StrEnum


class ImageOcrQualityStatus(StrEnum):
    TEXT_FOUND = "TEXT_FOUND"
    NO_TEXT = "NO_TEXT"
    LOW_CONFIDENCE_TEXT = "LOW_CONFIDENCE_TEXT"


class NameplateTextStatus(StrEnum):
    LIKELY_NAMEPLATE_TEXT = "LIKELY_NAMEPLATE_TEXT"
    GENERIC_TEXT = "GENERIC_TEXT"
    NO_TEXT = "NO_TEXT"
    UNKNOWN = "UNKNOWN"
