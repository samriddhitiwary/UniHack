"""Deterministic materialization of completed human review decisions."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    ReviewedMaterializationAttributeLimitExceededError,
    ReviewedMaterializationDecisionInvalidError,
    ReviewedMaterializationLineageMismatchError,
    ReviewedMaterializationRequiredAttributeUnresolvedError,
    ReviewedMaterializationReviewNotCompletedError,
    ReviewedMaterializationSchemaMismatchError,
    ReviewedMaterializationUnknownAttributeError,
)
from app.domain.attribute_normalization import AttributeNormalizationResult
from app.domain.attribute_selection import AttributeSelectionResult
from app.domain.attribute_validation import AttributeValidationResult
from app.domain.category_schemas import CategoryAttributeSchema
from app.domain.product_review import (
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    ProductReviewSession,
    ProductReviewSessionStatus,
)
from app.domain.reviewed_attributes import (
    FinalAttributeOrigin,
    FinalReviewedAttribute,
    FinalReviewedAttributeSet,
)

logger = logging.getLogger(__name__)


class ReviewedAttributeMaterializationEngine:
    def __init__(
        self,
        *,
        max_attributes: int = 100,
        max_value_characters: int = 10_000,
        max_manual_raw_characters: int = 10_000,
    ) -> None:
        self._max_attributes = max_attributes
        self._max_value = max_value_characters
        self._max_raw = max_manual_raw_characters

    def materialize(
        self,
        *,
        job_id: UUID,
        review: ProductReviewSession,
        current_decisions: Sequence[AttributeReviewDecision],
        schema: CategoryAttributeSchema,
        selection_result: AttributeSelectionResult,
        validation_result: AttributeValidationResult,
        normalization_result: AttributeNormalizationResult,
        now: datetime | None = None,
    ) -> FinalReviewedAttributeSet:
        if review.status is not ProductReviewSessionStatus.COMPLETED:
            raise ReviewedMaterializationReviewNotCompletedError()
        self._lineage(review, schema, selection_result, validation_result, normalization_result)
        if (
            len(schema.attributes) > self._max_attributes
            or len(current_decisions) > self._max_attributes
        ):
            raise ReviewedMaterializationAttributeLimitExceededError()
        decisions = {item.attribute_name: item for item in current_decisions}
        if len(decisions) != len(current_decisions):
            raise ReviewedMaterializationDecisionInvalidError()
        schema_names = {item.canonical_name for item in schema.attributes}
        if set(decisions) - schema_names:
            raise ReviewedMaterializationUnknownAttributeError()
        timestamp = (now or datetime.now(UTC)).astimezone(UTC)
        normalized = {
            item.normalized_candidate_id: item for item in normalization_result.candidates
        }
        validated = {item.normalized_candidate_id: item for item in validation_result.assessments}
        selected = {item.attribute_name: item for item in selection_result.attributes}
        output: list[FinalReviewedAttribute] = []
        for definition in sorted(schema.attributes, key=lambda item: item.display_order):
            decision = decisions.get(definition.canonical_name)
            if decision is None or decision.decision_type is AttributeReviewDecisionType.REJECT_ALL:
                if definition.required:
                    raise ReviewedMaterializationRequiredAttributeUnresolvedError()
                continue
            if decision.approved_value is None or len(decision.approved_value) > self._max_value:
                raise ReviewedMaterializationDecisionInvalidError()
            if decision.decision_type is AttributeReviewDecisionType.MANUAL_OVERRIDE:
                if (
                    decision.manual_raw_value is None
                    or len(decision.manual_raw_value) > self._max_raw
                ):
                    raise ReviewedMaterializationDecisionInvalidError()
                attribute = FinalReviewedAttribute(
                    attribute_name=definition.canonical_name,
                    attribute_display_name=definition.display_name,
                    data_type=definition.data_type,
                    required=definition.required,
                    display_order=definition.display_order,
                    value=decision.approved_value,
                    unit=decision.approved_unit,
                    origin=FinalAttributeOrigin.HUMAN_OVERRIDE,
                    review_decision_id=decision.decision_id,
                    review_decision_sequence=decision.decision_sequence,
                    reviewer_id=decision.reviewer_id,
                    candidate_id=None,
                    source_candidate_id=None,
                    source_id=None,
                    manual_raw_value=decision.manual_raw_value,
                    manual_raw_unit=decision.manual_raw_unit,
                    selection_confidence_bp=None,
                    validation_status=None,
                    created_at=timestamp,
                )
            else:
                candidate = normalized.get(decision.candidate_id or "")
                assessment = validated.get(decision.candidate_id or "")
                proposal = selected.get(definition.canonical_name)
                candidate_id = decision.candidate_id or ""
                if (
                    candidate is None
                    or assessment is None
                    or proposal is None
                    or candidate.attribute_name != definition.canonical_name
                    or assessment.attribute_name != definition.canonical_name
                    or candidate.normalized_value != decision.approved_value
                    or candidate.normalized_unit != decision.approved_unit
                    or (
                        decision.decision_type is AttributeReviewDecisionType.APPROVE_PROPOSED
                        and candidate_id != proposal.primary_candidate_id
                    )
                    or (
                        decision.decision_type is AttributeReviewDecisionType.APPROVE_CANDIDATE
                        and candidate_id not in proposal.review_candidate_ids
                    )
                ):
                    raise ReviewedMaterializationDecisionInvalidError()
                origin = (
                    FinalAttributeOrigin.APPROVED_PROPOSED
                    if decision.decision_type is AttributeReviewDecisionType.APPROVE_PROPOSED
                    else FinalAttributeOrigin.APPROVED_CANDIDATE
                )
                attribute = FinalReviewedAttribute(
                    attribute_name=definition.canonical_name,
                    attribute_display_name=definition.display_name,
                    data_type=definition.data_type,
                    required=definition.required,
                    display_order=definition.display_order,
                    value=decision.approved_value,
                    unit=decision.approved_unit,
                    origin=origin,
                    review_decision_id=decision.decision_id,
                    review_decision_sequence=decision.decision_sequence,
                    reviewer_id=decision.reviewer_id,
                    candidate_id=candidate.normalized_candidate_id,
                    source_candidate_id=candidate.source_candidate_id,
                    source_id=candidate.source_id,
                    manual_raw_value=None,
                    manual_raw_unit=None,
                    selection_confidence_bp=proposal.selection_confidence_bp,
                    validation_status=assessment.status,
                    created_at=timestamp,
                )
            output.append(attribute)
            logger.info(
                "event=reviewed_attribute_materialization.attribute_materialized job_id=%s "
                "attribute_name=%s origin=%s",
                job_id,
                attribute.attribute_name,
                attribute.origin.value,
            )
        return FinalReviewedAttributeSet.create(
            job_id=job_id,
            product_id=review.product_id,
            review_id=review.review_id,
            selection_id=review.selection_id,
            conflict_detection_id=review.conflict_detection_id,
            validation_id=review.validation_id,
            completeness_id=review.completeness_id,
            normalization_id=review.normalization_id,
            extraction_id=review.extraction_id,
            classification_id=review.classification_id,
            category=review.category,
            schema_version=review.schema_version,
            schema_fingerprint=review.schema_fingerprint,
            attributes=tuple(output),
            required_count=sum(a.required for a in schema.attributes),
            optional_count=sum(not a.required for a in schema.attributes),
            now=timestamp,
        )

    @staticmethod
    def _lineage(
        review: ProductReviewSession,
        schema: CategoryAttributeSchema,
        selection: AttributeSelectionResult,
        validation: AttributeValidationResult,
        normalization: AttributeNormalizationResult,
    ) -> None:
        if (
            schema.category != review.category
            or schema.version != review.schema_version
            or schema.schema_fingerprint != review.schema_fingerprint
        ):
            raise ReviewedMaterializationSchemaMismatchError()
        if (
            selection.selection_id != review.selection_id
            or selection.product_id != review.product_id
            or selection.validation_id != review.validation_id
            or selection.normalization_id != review.normalization_id
            or selection.conflict_detection_id != review.conflict_detection_id
            or selection.completeness_id != review.completeness_id
            or validation.validation_id != review.validation_id
            or normalization.normalization_id != review.normalization_id
        ):
            raise ReviewedMaterializationLineageMismatchError()
        common = (
            review.product_id,
            review.extraction_id,
            review.classification_id,
            review.category,
            review.schema_version,
            review.schema_fingerprint,
        )
        if any(
            (
                value.product_id,
                value.extraction_id,
                value.classification_id,
                value.category,
                value.schema_version,
                value.schema_fingerprint,
            )
            != common
            for value in (selection, validation, normalization)
        ):
            raise ReviewedMaterializationLineageMismatchError()
