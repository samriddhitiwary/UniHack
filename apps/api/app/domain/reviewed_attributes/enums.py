"""Final reviewed attribute enumerations."""

from enum import StrEnum


class FinalAttributeOrigin(StrEnum):
    APPROVED_PROPOSED = "APPROVED_PROPOSED"
    APPROVED_CANDIDATE = "APPROVED_CANDIDATE"
    HUMAN_OVERRIDE = "HUMAN_OVERRIDE"


class ReviewedAttributeSetStatus(StrEnum):
    MATERIALIZED = "MATERIALIZED"
