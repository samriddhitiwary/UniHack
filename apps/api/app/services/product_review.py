"""Application service for human product-review sessions and decisions."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.exceptions import (
    AttributeCompletenessRepositoryError,
    AttributeConflictRepositoryError,
    AttributeNormalizationRepositoryError,
    AttributeSelectionNotFoundForReviewError,
    AttributeSelectionRepositoryError,
    AttributeValidationRepositoryError,
    CategoryAttributeSchemaRepositoryError,
    ProductNotFoundError,
    ProductRepositoryError,
    ProductReviewAlreadyCompletedError,
    ProductReviewAlreadyExistsError,
    ProductReviewAttributeNotFoundError,
    ProductReviewCandidateNotApprovableError,
    ProductReviewCandidateNotFoundError,
    ProductReviewDecisionLimitExceededError,
    ProductReviewDecisionNotAllowedError,
    ProductReviewNotFoundError,
    ProductReviewRepositoryError,
    ProductReviewRequiredAttributesUnresolvedError,
    ProductReviewSelectionLineageInvalidError,
    ProductReviewVersionConflictError,
)
from app.domain.attribute_normalization import AttributeNormalizationResult
from app.domain.attribute_selection import AttributeSelectionResult, AttributeSelectionStatus
from app.domain.attribute_validation import (
    AttributeValidationResult,
    CandidateValidationStatus,
)
from app.domain.category_schemas import CategoryAttributeSchema
from app.domain.product_review import (
    RESOLVING_DECISION_TYPES,
    AttributeReviewDecision,
    AttributeReviewDecisionType,
    CurrentAttributeReviewDecision,
    ProductReviewSession,
    ProductReviewSessionStatus,
    ReviewDecisionPage,
)
from app.repositories.attribute_completeness import AttributeCompletenessResultRepository
from app.repositories.attribute_conflicts import AttributeConflictDetectionResultRepository
from app.repositories.attribute_normalization import AttributeNormalizationResultRepository
from app.repositories.attribute_selection import AttributeSelectionResultRepository
from app.repositories.attribute_validation import AttributeValidationResultRepository
from app.repositories.category_schemas import CategoryAttributeSchemaRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.products import ProductRepository
from app.schemas.product_review import AttributeReviewDecisionCreate
from app.services.review_manual_override import ReviewManualOverride

logger = logging.getLogger(__name__)

UPSTREAM_STORAGE_ERRORS = (
    ProductRepositoryError,
    AttributeSelectionRepositoryError,
    AttributeConflictRepositoryError,
    AttributeValidationRepositoryError,
    AttributeCompletenessRepositoryError,
    AttributeNormalizationRepositoryError,
    CategoryAttributeSchemaRepositoryError,
)


class ProductReviewService:
    def __init__(
        self,
        *,
        product_repository: ProductRepository,
        selection_repository: AttributeSelectionResultRepository,
        conflict_repository: AttributeConflictDetectionResultRepository,
        validation_repository: AttributeValidationResultRepository,
        completeness_repository: AttributeCompletenessResultRepository,
        normalization_repository: AttributeNormalizationResultRepository,
        schema_repository: CategoryAttributeSchemaRepository,
        review_repository: ProductReviewRepository,
        manual_override: ReviewManualOverride,
        max_decisions: int = 1_000,
        max_attributes: int = 100,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._products = product_repository
        self._selections = selection_repository
        self._conflicts = conflict_repository
        self._validations = validation_repository
        self._completeness = completeness_repository
        self._normalizations = normalization_repository
        self._schemas = schema_repository
        self._reviews = review_repository
        self._manual = manual_override
        self._max_decisions = max_decisions
        self._max_attributes = max_attributes
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_review(self, *, product_id: UUID, selection_id: UUID) -> ProductReviewSession:
        product = self._read(self._products.get_by_id, product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        selection = self._read(self._selections.get_by_id, selection_id)
        if selection is None:
            raise AttributeSelectionNotFoundForReviewError()
        if selection.product_id != product_id or product.category != selection.category:
            raise ProductReviewSelectionLineageInvalidError()
        if len(selection.attributes) > self._max_attributes:
            raise ProductReviewSelectionLineageInvalidError()
        self._load_and_validate_lineage(selection)
        if self._reviews.get_by_selection_id(selection_id) is not None:
            raise ProductReviewAlreadyExistsError()
        review = ProductReviewSession.create(selection, self._clock())
        stored = self._reviews.create(review)
        logger.info(
            "event=product_review.created review_id=%s product_id=%s selection_id=%s version=%s",
            stored.review_id,
            stored.product_id,
            stored.selection_id,
            stored.version,
        )
        return stored

    def get_review(self, *, product_id: UUID, review_id: UUID) -> ProductReviewSession:
        review = self._reviews.get_by_id(review_id)
        if review is None or review.product_id != product_id:
            raise ProductReviewNotFoundError()
        return review

    def list_decisions(
        self,
        *,
        product_id: UUID,
        review_id: UUID,
        limit: int,
        cursor: str | None,
    ) -> ReviewDecisionPage:
        self.get_review(product_id=product_id, review_id=review_id)
        return self._reviews.list_decisions(review_id, limit=limit, cursor=cursor)

    def submit_decision(
        self,
        *,
        product_id: UUID,
        review_id: UUID,
        attribute_name: str,
        request: AttributeReviewDecisionCreate,
    ) -> AttributeReviewDecision:
        review = self.get_review(product_id=product_id, review_id=review_id)
        self._assert_writable(review, request.version)
        if review.decision_count >= self._max_decisions:
            raise ProductReviewDecisionLimitExceededError()
        selection = self._selection_for(review)
        selected_attribute = next(
            (item for item in selection.attributes if item.attribute_name == attribute_name), None
        )
        if selected_attribute is None:
            raise ProductReviewAttributeNotFoundError()
        validation, normalization, schema = self._decision_inputs(review, selection)
        approved_value: str | None = None
        approved_unit: str | None = None
        candidate_id: str | None = None
        manual_raw_value: str | None = None
        manual_raw_unit: str | None = None
        if request.decision_type is AttributeReviewDecisionType.APPROVE_PROPOSED:
            if (
                selected_attribute.selection_status is not AttributeSelectionStatus.AUTO_SELECTED
                or selected_attribute.primary_candidate_id is None
                or selected_attribute.proposed_value is None
            ):
                raise ProductReviewDecisionNotAllowedError()
            candidate_id = selected_attribute.primary_candidate_id
            approved_value = selected_attribute.proposed_value
            approved_unit = selected_attribute.proposed_unit
        elif request.decision_type is AttributeReviewDecisionType.APPROVE_CANDIDATE:
            candidate_id = request.candidate_id
            allowed_ids = {
                *selected_attribute.supporting_candidate_ids,
                *selected_attribute.review_candidate_ids,
            }
            if candidate_id is None or candidate_id not in allowed_ids:
                raise ProductReviewCandidateNotFoundError()
            assessment = next(
                (
                    item
                    for item in validation.assessments
                    if item.normalized_candidate_id == candidate_id
                ),
                None,
            )
            candidate = next(
                (
                    item
                    for item in normalization.candidates
                    if item.normalized_candidate_id == candidate_id
                ),
                None,
            )
            if (
                assessment is None
                or candidate is None
                or assessment.attribute_name != attribute_name
                or candidate.attribute_name != attribute_name
            ):
                raise ProductReviewCandidateNotFoundError()
            if assessment.status not in {
                CandidateValidationStatus.VALID,
                CandidateValidationStatus.VALID_WITH_WARNINGS,
            }:
                raise ProductReviewCandidateNotApprovableError()
            if assessment.normalized_value is None:
                raise ProductReviewCandidateNotApprovableError()
            approved_value, approved_unit = assessment.normalized_value, assessment.normalized_unit
        elif request.decision_type is AttributeReviewDecisionType.MANUAL_OVERRIDE:
            definition = next(
                (item for item in schema.attributes if item.canonical_name == attribute_name), None
            )
            if definition is None or request.manual_value is None:
                raise ProductReviewAttributeNotFoundError()
            outcome = self._manual.normalize_and_validate(
                definition=definition,
                raw_value=request.manual_value,
                raw_unit=request.manual_unit,
            )
            manual_raw_value, manual_raw_unit = request.manual_value, request.manual_unit
            approved_value, approved_unit = outcome.approved_value, outcome.approved_unit
        timestamp = self._clock()
        decision = AttributeReviewDecision(
            decision_id=uuid4(),
            review_id=review.review_id,
            product_id=review.product_id,
            decision_sequence=review.decision_count + 1,
            attribute_name=attribute_name,
            decision_type=request.decision_type,
            candidate_id=candidate_id,
            approved_value=approved_value,
            approved_unit=approved_unit,
            manual_raw_value=manual_raw_value,
            manual_raw_unit=manual_raw_unit,
            comment=request.comment,
            reviewer_id=request.reviewer_id,
            review_version=review.version + 1,
            created_at=timestamp,
        )
        current = CurrentAttributeReviewDecision.from_decision(decision)
        current_values = {
            item.attribute_name: item for item in self._reviews.list_current_decisions(review_id)
        }
        current_values[attribute_name] = current
        required_resolved, optional_resolved = self._resolved_counts(selection, current_values)
        updated = review.after_decision(
            required_resolved=required_resolved,
            optional_resolved=optional_resolved,
            now=timestamp,
        )
        self._reviews.append_decision(updated, decision, current, expected_version=request.version)
        logger.info(
            "event=product_review.decision_submitted review_id=%s product_id=%s "
            "attribute_name=%s decision_type=%s reviewer_id=%s version=%s sequence=%s",
            review_id,
            product_id,
            attribute_name,
            decision.decision_type.value,
            decision.reviewer_id,
            updated.version,
            decision.decision_sequence,
        )
        return decision

    def complete_review(
        self, *, product_id: UUID, review_id: UUID, version: int, reviewer_id: str
    ) -> ProductReviewSession:
        review = self.get_review(product_id=product_id, review_id=review_id)
        self._assert_writable(review, version)
        selection = self._selection_for(review)
        current = {
            item.attribute_name: item for item in self._reviews.list_current_decisions(review_id)
        }
        required_resolved, optional_resolved = self._resolved_counts(selection, current)
        unresolved = [
            item.attribute_name
            for item in selection.attributes
            if item.required
            and (
                item.attribute_name not in current
                or current[item.attribute_name].decision_type not in RESOLVING_DECISION_TYPES
            )
        ]
        if unresolved or required_resolved != review.required_attribute_count:
            raise ProductReviewRequiredAttributesUnresolvedError(
                details={"attributeNames": unresolved[: self._max_attributes]}
            )
        if (
            review.required_resolved_count != required_resolved
            or review.optional_resolved_count != optional_resolved
        ):
            raise ProductReviewSelectionLineageInvalidError()
        completed = review.complete(self._clock())
        stored = self._reviews.complete(completed, expected_version=version)
        logger.info(
            "event=product_review.completed review_id=%s product_id=%s reviewer_id=%s version=%s",
            review_id,
            product_id,
            reviewer_id,
            stored.version,
        )
        return stored

    @staticmethod
    def _assert_writable(review: ProductReviewSession, version: int) -> None:
        if review.status is ProductReviewSessionStatus.COMPLETED:
            raise ProductReviewAlreadyCompletedError()
        if review.version != version:
            raise ProductReviewVersionConflictError()

    def _selection_for(self, review: ProductReviewSession) -> AttributeSelectionResult:
        selection = self._read(self._selections.get_by_id, review.selection_id)
        if selection is None:
            raise AttributeSelectionNotFoundForReviewError()
        if (
            selection.product_id != review.product_id
            or selection.conflict_detection_id != review.conflict_detection_id
            or selection.validation_id != review.validation_id
            or selection.completeness_id != review.completeness_id
            or selection.normalization_id != review.normalization_id
            or selection.extraction_id != review.extraction_id
            or selection.classification_id != review.classification_id
            or selection.category != review.category
            or selection.schema_version != review.schema_version
            or selection.schema_fingerprint != review.schema_fingerprint
        ):
            raise ProductReviewSelectionLineageInvalidError()
        return selection

    def _load_and_validate_lineage(self, selection: AttributeSelectionResult) -> None:
        conflict = self._read(self._conflicts.get_by_id, selection.conflict_detection_id)
        validation = self._read(self._validations.get_by_id, selection.validation_id)
        completeness = self._read(self._completeness.get_by_id, selection.completeness_id)
        normalization = self._read(self._normalizations.get_by_id, selection.normalization_id)
        schema = self._read(
            self._schemas.get_by_category_and_version, selection.category, selection.schema_version
        )
        if any(
            value is None for value in (conflict, validation, completeness, normalization, schema)
        ):
            raise ProductReviewSelectionLineageInvalidError()
        assert conflict is not None and validation is not None and completeness is not None
        assert normalization is not None and schema is not None
        expected = (
            selection.product_id,
            selection.normalization_id,
            selection.extraction_id,
            selection.classification_id,
            selection.category,
            selection.schema_version,
            selection.schema_fingerprint,
        )
        for value in (conflict, validation, completeness):
            actual = (
                value.product_id,
                value.normalization_id,
                value.extraction_id,
                value.classification_id,
                value.category,
                value.schema_version,
                value.schema_fingerprint,
            )
            if actual != expected:
                raise ProductReviewSelectionLineageInvalidError()
        if (
            normalization.product_id,
            normalization.normalization_id,
            normalization.extraction_id,
            normalization.classification_id,
            normalization.category,
            normalization.schema_version,
            normalization.schema_fingerprint,
        ) != expected:
            raise ProductReviewSelectionLineageInvalidError()
        if completeness.conflict_detection_id != conflict.conflict_detection_id:
            raise ProductReviewSelectionLineageInvalidError()
        if (
            schema.category != selection.category
            or schema.version != selection.schema_version
            or schema.schema_fingerprint != selection.schema_fingerprint
        ):
            raise ProductReviewSelectionLineageInvalidError()

    def _decision_inputs(
        self, review: ProductReviewSession, selection: AttributeSelectionResult
    ) -> tuple[AttributeValidationResult, AttributeNormalizationResult, CategoryAttributeSchema]:
        validation = self._read(self._validations.get_by_id, review.validation_id)
        normalization = self._read(self._normalizations.get_by_id, review.normalization_id)
        schema = self._read(
            self._schemas.get_by_category_and_version, review.category, review.schema_version
        )
        if validation is None or normalization is None or schema is None:
            raise ProductReviewSelectionLineageInvalidError()
        if (
            validation.product_id != review.product_id
            or validation.normalization_id != review.normalization_id
            or validation.extraction_id != review.extraction_id
            or validation.classification_id != review.classification_id
            or validation.schema_fingerprint != review.schema_fingerprint
            or normalization.product_id != review.product_id
            or normalization.extraction_id != review.extraction_id
            or normalization.classification_id != review.classification_id
            or normalization.schema_fingerprint != review.schema_fingerprint
            or schema.schema_fingerprint != review.schema_fingerprint
            or selection.validation_id != validation.validation_id
        ):
            raise ProductReviewSelectionLineageInvalidError()
        return validation, normalization, schema

    @staticmethod
    def _resolved_counts(
        selection: AttributeSelectionResult,
        current: dict[str, CurrentAttributeReviewDecision],
    ) -> tuple[int, int]:
        required = optional = 0
        for attribute in selection.attributes:
            value = current.get(attribute.attribute_name)
            if value is None or value.decision_type not in RESOLVING_DECISION_TYPES:
                continue
            if attribute.required:
                required += 1
            else:
                optional += 1
        return required, optional

    @staticmethod
    def _read[T](operation: Callable[..., T], *args: object) -> T:
        try:
            return operation(*args)
        except UPSTREAM_STORAGE_ERRORS as exc:
            raise ProductReviewRepositoryError("review dependency is unavailable") from exc
