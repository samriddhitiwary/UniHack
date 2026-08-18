"""Human product-review enumerations."""

from enum import StrEnum


class ProductReviewSessionStatus(StrEnum):
    OPEN = "OPEN"
    COMPLETED = "COMPLETED"


class AttributeReviewDecisionType(StrEnum):
    APPROVE_CANDIDATE = "APPROVE_CANDIDATE"
    APPROVE_PROPOSED = "APPROVE_PROPOSED"
    REJECT_ALL = "REJECT_ALL"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


RESOLVING_DECISION_TYPES = frozenset(
    {
        AttributeReviewDecisionType.APPROVE_CANDIDATE,
        AttributeReviewDecisionType.APPROVE_PROPOSED,
        AttributeReviewDecisionType.MANUAL_OVERRIDE,
    }
)
