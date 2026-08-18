"""Immutable authoritative reviewed attributes and aggregate."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.domain.reviewed_attributes.enums import FinalAttributeOrigin, ReviewedAttributeSetStatus


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class FinalReviewedAttribute:
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    required: bool
    display_order: int
    value: str
    unit: str | None
    origin: FinalAttributeOrigin
    review_decision_id: UUID
    review_decision_sequence: int
    reviewer_id: str
    candidate_id: str | None
    source_candidate_id: str | None
    source_id: UUID | None
    manual_raw_value: str | None
    manual_raw_unit: str | None
    selection_confidence_bp: int | None
    validation_status: CandidateValidationStatus | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.attribute_name or not self.attribute_display_name or not self.value:
            raise ValueError("reviewed attribute identity and value are required")
        if self.display_order < 1 or self.review_decision_sequence < 1:
            raise ValueError("reviewed attribute ordering is invalid")
        if (
            self.selection_confidence_bp is not None
            and not 0 <= self.selection_confidence_bp <= 10_000
        ):
            raise ValueError("selection confidence is invalid")
        candidate_origin = self.origin in {
            FinalAttributeOrigin.APPROVED_PROPOSED,
            FinalAttributeOrigin.APPROVED_CANDIDATE,
        }
        if candidate_origin and (
            self.candidate_id is None
            or self.source_candidate_id is None
            or self.source_id is None
            or self.validation_status is None
            or self.manual_raw_value is not None
            or self.manual_raw_unit is not None
        ):
            raise ValueError("candidate-origin lineage is invalid")
        if self.origin is FinalAttributeOrigin.HUMAN_OVERRIDE and (
            self.candidate_id is not None
            or self.source_candidate_id is not None
            or self.source_id is not None
            or self.manual_raw_value is None
            or self.selection_confidence_bp is not None
            or self.validation_status is not None
        ):
            raise ValueError("human-override lineage is invalid")
        object.__setattr__(self, "created_at", _utc(self.created_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class FinalReviewedAttributeSet:
    materialization_id: UUID
    job_id: UUID
    product_id: UUID
    review_id: UUID
    selection_id: UUID
    conflict_detection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: ReviewedAttributeSetStatus
    required_attribute_count: int
    materialized_required_count: int
    optional_attribute_count: int
    materialized_optional_count: int
    unresolved_optional_count: int
    attribute_count: int
    attributes: tuple[FinalReviewedAttribute, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        required = tuple(item for item in self.attributes if item.required)
        optional = tuple(item for item in self.attributes if not item.required)
        if self.attribute_count != len(self.attributes) or len(
            {a.attribute_name for a in self.attributes}
        ) != len(self.attributes):
            raise ValueError("reviewed attribute count or uniqueness is invalid")
        if (
            self.materialized_required_count != len(required)
            or self.materialized_required_count != self.required_attribute_count
        ):
            raise ValueError("required reviewed counts are inconsistent")
        if self.materialized_optional_count != len(
            optional
        ) or self.unresolved_optional_count != self.optional_attribute_count - len(optional):
            raise ValueError("optional reviewed counts are inconsistent")
        if tuple(sorted(self.attributes, key=lambda item: item.display_order)) != self.attributes:
            raise ValueError("reviewed attributes must follow schema order")
        object.__setattr__(self, "created_at", _utc(self.created_at))

    @classmethod
    def create(
        cls,
        *,
        attributes: tuple[FinalReviewedAttribute, ...],
        required_count: int,
        optional_count: int,
        now: datetime,
        **lineage: object,
    ) -> "FinalReviewedAttributeSet":
        materialized_required = sum(item.required for item in attributes)
        materialized_optional = len(attributes) - materialized_required
        return cls(
            materialization_id=uuid4(),
            status=ReviewedAttributeSetStatus.MATERIALIZED,
            required_attribute_count=required_count,
            materialized_required_count=materialized_required,
            optional_attribute_count=optional_count,
            materialized_optional_count=materialized_optional,
            unresolved_optional_count=optional_count - materialized_optional,
            attribute_count=len(attributes),
            attributes=attributes,
            engine="reviewed-attribute-materializer-v1",
            engine_version="1.0",
            created_at=now,
            **lineage,  # type: ignore[arg-type]
        )
