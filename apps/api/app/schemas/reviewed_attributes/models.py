"""Strict internal schemas for final reviewed attribute artifacts."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.domain.reviewed_attributes import FinalAttributeOrigin, ReviewedAttributeSetStatus
from app.schemas.products.models import to_camel


class ReviewedAttributeSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class FinalReviewedAttributeRecord(ReviewedAttributeSchema):
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    required: bool
    display_order: int = Field(gt=0)
    value: str
    unit: str | None
    origin: FinalAttributeOrigin
    review_decision_id: UUID
    review_decision_sequence: int = Field(gt=0)
    reviewer_id: str
    candidate_id: str | None
    source_candidate_id: str | None
    source_id: UUID | None
    manual_raw_value: str | None
    manual_raw_unit: str | None
    selection_confidence_bp: int | None = Field(default=None, ge=0, le=10_000)
    validation_status: CandidateValidationStatus | None
    created_at: AwareDatetime


class FinalReviewedAttributeSetRecord(ReviewedAttributeSchema):
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
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    status: ReviewedAttributeSetStatus
    required_attribute_count: int = Field(ge=0)
    materialized_required_count: int = Field(ge=0)
    optional_attribute_count: int = Field(ge=0)
    materialized_optional_count: int = Field(ge=0)
    unresolved_optional_count: int = Field(ge=0)
    attribute_count: int = Field(ge=0)
    attributes: tuple[FinalReviewedAttributeRecord, ...]
    engine: str
    engine_version: str
    created_at: AwareDatetime
