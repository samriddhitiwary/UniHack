"""Resolve CURRENT projections to the latest immutable review decisions."""

from collections.abc import Sequence
from uuid import UUID

from app.core.exceptions import ReviewedMaterializationReviewStateInvalidError
from app.domain.product_review import AttributeReviewDecision, CurrentAttributeReviewDecision


class ReviewDecisionResolver:
    def resolve(
        self,
        *,
        review_id: UUID,
        product_id: UUID,
        current: Sequence[CurrentAttributeReviewDecision],
        history: Sequence[AttributeReviewDecision],
    ) -> dict[str, AttributeReviewDecision]:
        if len({item.attribute_name for item in current}) != len(current):
            raise ReviewedMaterializationReviewStateInvalidError()
        by_id = {item.decision_id: item for item in history}
        if len(by_id) != len(history):
            raise ReviewedMaterializationReviewStateInvalidError()
        latest: dict[str, AttributeReviewDecision] = {}
        for decision in history:
            if decision.review_id != review_id or decision.product_id != product_id:
                raise ReviewedMaterializationReviewStateInvalidError()
            existing = latest.get(decision.attribute_name)
            if existing is None or decision.decision_sequence > existing.decision_sequence:
                latest[decision.attribute_name] = decision
        resolved: dict[str, AttributeReviewDecision] = {}
        for projection in current:
            resolved_decision = by_id.get(projection.decision_id)
            if (
                resolved_decision is None
                or resolved_decision.attribute_name != projection.attribute_name
                or resolved_decision.decision_sequence != projection.decision_sequence
                or resolved_decision.decision_type is not projection.decision_type
                or latest.get(projection.attribute_name) is not resolved_decision
            ):
                raise ReviewedMaterializationReviewStateInvalidError()
            resolved[projection.attribute_name] = resolved_decision
        return resolved
