"""Strict internal schemas for attribute selection boundaries."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_conflicts import AttributeConflictType, AttributeConsensusStatus
from app.domain.attribute_selection import (
    AttributeSelectionStatus,
    ProductReviewStatus,
    SelectionReasonCode,
)
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class SelectionSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProposedAttributeSelectionRecord(SelectionSchema):
    attribute_name: str
    attribute_display_name: str
    required: bool
    display_order: int = Field(gt=0)
    selection_status: AttributeSelectionStatus
    review_required: bool
    proposed_value: str | None
    proposed_unit: str | None
    primary_candidate_id: str | None
    supporting_candidate_ids: tuple[str, ...]
    review_candidate_ids: tuple[str, ...]
    candidate_count: int = Field(ge=0)
    valid_candidate_count: int = Field(ge=0)
    distinct_source_count: int = Field(ge=0)
    consensus_status: AttributeConsensusStatus | None
    conflict_type: AttributeConflictType | None
    selection_confidence_bp: int = Field(ge=0, le=10_000)
    reason_codes: tuple[SelectionReasonCode, ...]
    warning_codes: tuple[str, ...]


class ProductReviewPreparationSummaryRecord(SelectionSchema):
    required_attribute_count: int = Field(ge=0)
    auto_selected_required_count: int = Field(ge=0)
    review_required_required_count: int = Field(ge=0)
    missing_required_count: int = Field(ge=0)
    invalid_required_count: int = Field(ge=0)
    optional_attribute_count: int = Field(ge=0)
    auto_selected_optional_count: int = Field(ge=0)
    review_required_optional_count: int = Field(ge=0)
    unresolved_optional_count: int = Field(ge=0)
    auto_selected_total_count: int = Field(ge=0)
    review_required_total_count: int = Field(ge=0)
    overall_status: ProductReviewStatus


class AttributeSelectionResultRecord(SelectionSchema):
    selection_id: UUID
    job_id: UUID
    product_id: UUID
    conflict_detection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    overall_status: ProductReviewStatus
    attribute_count: int = Field(ge=0)
    auto_selected_count: int = Field(ge=0)
    review_required_count: int = Field(ge=0)
    no_candidate_count: int = Field(ge=0)
    no_valid_candidate_count: int = Field(ge=0)
    required_auto_selected_count: int = Field(ge=0)
    required_review_required_count: int = Field(ge=0)
    required_missing_count: int = Field(ge=0)
    required_invalid_count: int = Field(ge=0)
    attributes: tuple[ProposedAttributeSelectionRecord, ...]
    review_summary: ProductReviewPreparationSummaryRecord
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: AwareDatetime
