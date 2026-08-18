"""Product-review persistence contract."""

from typing import Protocol
from uuid import UUID

from app.domain.product_review import (
    AttributeReviewDecision,
    CurrentAttributeReviewDecision,
    ProductReviewSession,
    ReviewDecisionPage,
)


class ProductReviewRepository(Protocol):
    def create(self, review: ProductReviewSession) -> ProductReviewSession: ...
    def get_by_id(self, review_id: UUID) -> ProductReviewSession | None: ...
    def get_by_selection_id(self, selection_id: UUID) -> ProductReviewSession | None: ...
    def append_decision(
        self,
        review: ProductReviewSession,
        decision: AttributeReviewDecision,
        current: CurrentAttributeReviewDecision,
        *,
        expected_version: int,
    ) -> ProductReviewSession: ...
    def list_decisions(
        self, review_id: UUID, *, limit: int, cursor: str | None = None
    ) -> ReviewDecisionPage: ...
    def list_current_decisions(
        self, review_id: UUID
    ) -> tuple[CurrentAttributeReviewDecision, ...]: ...
    def complete(
        self, review: ProductReviewSession, *, expected_version: int
    ) -> ProductReviewSession: ...
