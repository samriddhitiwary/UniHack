"""Project final reviewed attributes without revalidation or raw evidence duplication."""

from dataclasses import dataclass

from app.core.exceptions import (
    CatalogProjectionAttributeLimitExceededError,
    CatalogProjectionRequiredAttributesIncompleteError,
    CatalogProjectionValueLimitExceededError,
)
from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.catalog_projection import CatalogWarningReason, CommerceCatalogAttribute
from app.domain.reviewed_attributes import (
    FinalAttributeOrigin,
    FinalReviewedAttributeSet,
    ReviewedAttributeSetStatus,
)


@dataclass(frozen=True, slots=True)
class ReviewedAttributeProjection:
    attributes: tuple[CommerceCatalogAttribute, ...]
    warnings: tuple[CatalogWarningReason, ...]


class CatalogReviewedAttributeProjector:
    def __init__(self, *, max_attributes: int = 100, max_value_characters: int = 10_000) -> None:
        self._max_attributes = max_attributes
        self._max_value = max_value_characters

    def project(self, materialization: FinalReviewedAttributeSet) -> ReviewedAttributeProjection:
        if materialization.status is not ReviewedAttributeSetStatus.MATERIALIZED:
            raise CatalogProjectionRequiredAttributesIncompleteError()
        if (
            materialization.materialized_required_count != materialization.required_attribute_count
            or sum(item.required for item in materialization.attributes)
            != materialization.required_attribute_count
        ):
            raise CatalogProjectionRequiredAttributesIncompleteError()
        if len(materialization.attributes) > self._max_attributes:
            raise CatalogProjectionAttributeLimitExceededError()
        if any(len(item.value) > self._max_value for item in materialization.attributes):
            raise CatalogProjectionValueLimitExceededError()
        attributes = tuple(
            CommerceCatalogAttribute(
                attribute_name=item.attribute_name,
                attribute_display_name=item.attribute_display_name,
                data_type=item.data_type,
                required=item.required,
                display_order=item.display_order,
                value=item.value,
                unit=item.unit,
                origin=item.origin,
                review_decision_id=item.review_decision_id,
                candidate_id=item.candidate_id,
                source_id=item.source_id,
                validation_status=item.validation_status,
                created_at=item.created_at,
            )
            for item in sorted(materialization.attributes, key=lambda value: value.display_order)
        )
        warnings: list[CatalogWarningReason] = []
        if materialization.unresolved_optional_count:
            warnings.append(CatalogWarningReason.OPTIONAL_ATTRIBUTES_UNRESOLVED)
        if any(
            item.validation_status is CandidateValidationStatus.VALID_WITH_WARNINGS
            for item in materialization.attributes
        ):
            warnings.append(CatalogWarningReason.VALIDATION_WARNING_PRESENT)
        if any(
            item.origin is FinalAttributeOrigin.HUMAN_OVERRIDE
            for item in materialization.attributes
        ):
            warnings.append(CatalogWarningReason.HUMAN_OVERRIDE_PRESENT)
        return ReviewedAttributeProjection(attributes=attributes, warnings=tuple(warnings))
