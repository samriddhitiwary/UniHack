"""Product-review request and response schemas."""

from app.schemas.product_review.requests import (
    AttributeReviewDecisionCreate,
    ProductReviewComplete,
    ProductReviewCreate,
)
from app.schemas.product_review.responses import (
    AttributeReviewDecisionRecord,
    ProductReviewRecord,
    ReviewDecisionListResult,
)

__all__ = [
    "AttributeReviewDecisionCreate",
    "AttributeReviewDecisionRecord",
    "ProductReviewComplete",
    "ProductReviewCreate",
    "ProductReviewRecord",
    "ReviewDecisionListResult",
]
