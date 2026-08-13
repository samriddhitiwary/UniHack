"""Strict internal schemas for attribute completeness boundaries."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_completeness import (
    AttributeCompletenessState,
    AttributeCompletenessStatus,
)
from app.domain.attribute_conflicts import AttributeConflictType, AttributeConsensusStatus
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class AttributeCompletenessSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AttributeCompletenessAssessmentRecord(AttributeCompletenessSchema):
    attribute_name: str = Field(min_length=1)
    attribute_display_name: str = Field(min_length=1)
    required: bool
    display_order: int = Field(gt=0)
    state: AttributeCompletenessState
    candidate_count: int = Field(ge=0)
    comparable_candidate_count: int = Field(ge=0)
    distinct_source_count: int = Field(ge=0)
    consensus_status: AttributeConsensusStatus | None
    consensus_confidence_bp: int | None = Field(default=None, ge=0, le=10_000)
    conflict_type: AttributeConflictType | None
    available: bool
    resolved: bool
    verified: bool
    candidate_ids: tuple[str, ...]
    warning_codes: tuple[str, ...]


class AttributeCompletenessResultRecord(AttributeCompletenessSchema):
    completeness_id: UUID
    job_id: UUID
    product_id: UUID
    conflict_detection_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    status: AttributeCompletenessStatus
    required_attribute_count: int = Field(ge=0)
    required_available_count: int = Field(ge=0)
    required_resolved_count: int = Field(ge=0)
    required_verified_count: int = Field(ge=0)
    required_missing_count: int = Field(ge=0)
    required_conflicted_count: int = Field(ge=0)
    required_indeterminate_count: int = Field(ge=0)
    required_invalid_count: int = Field(ge=0)
    optional_attribute_count: int = Field(ge=0)
    optional_available_count: int = Field(ge=0)
    optional_resolved_count: int = Field(ge=0)
    optional_verified_count: int = Field(ge=0)
    optional_missing_count: int = Field(ge=0)
    optional_conflicted_count: int = Field(ge=0)
    optional_indeterminate_count: int = Field(ge=0)
    optional_invalid_count: int = Field(ge=0)
    total_attribute_count: int = Field(ge=0)
    total_available_count: int = Field(ge=0)
    total_resolved_count: int = Field(ge=0)
    total_verified_count: int = Field(ge=0)
    total_missing_count: int = Field(ge=0)
    total_conflicted_count: int = Field(ge=0)
    total_indeterminate_count: int = Field(ge=0)
    total_invalid_count: int = Field(ge=0)
    required_available_bp: int = Field(ge=0, le=10_000)
    required_resolved_bp: int = Field(ge=0, le=10_000)
    required_verified_bp: int = Field(ge=0, le=10_000)
    overall_available_bp: int = Field(ge=0, le=10_000)
    overall_resolved_bp: int = Field(ge=0, le=10_000)
    attributes: tuple[AttributeCompletenessAssessmentRecord, ...]
    warning_codes: tuple[str, ...]
    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    created_at: AwareDatetime
