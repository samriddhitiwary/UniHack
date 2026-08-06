"""Product-source domain enumerations."""

from enum import StrEnum


class ProductSourceType(StrEnum):
    PDF = "PDF"
    IMAGE = "IMAGE"
    CSV = "CSV"
    TEXT = "TEXT"


class ProductSourceStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
