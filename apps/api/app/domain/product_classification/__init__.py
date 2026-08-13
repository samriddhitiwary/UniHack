"""Product-classification domain model."""

from app.domain.product_classification.entities import (
    ClassificationEvidence,
    ClassificationMatch,
    ProductClassificationDecision,
    ProductClassificationResult,
)
from app.domain.product_classification.enums import (
    ClassificationEvidenceType,
    ClassificationSignalStrength,
    ProductClassificationStatus,
)

__all__ = [
    "ClassificationEvidence",
    "ClassificationEvidenceType",
    "ClassificationMatch",
    "ClassificationSignalStrength",
    "ProductClassificationDecision",
    "ProductClassificationResult",
    "ProductClassificationStatus",
]
