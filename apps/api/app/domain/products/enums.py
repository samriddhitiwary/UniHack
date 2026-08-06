"""Product domain enumerations."""

from enum import StrEnum


class ProductCategory(StrEnum):
    UNCLASSIFIED = "UNCLASSIFIED"
    CENTRIFUGAL_PUMP = "CENTRIFUGAL_PUMP"
    INDUCTION_MOTOR = "INDUCTION_MOTOR"


class ProductStatus(StrEnum):
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    READY_TO_PUBLISH = "READY_TO_PUBLISH"
    FAILED = "FAILED"
