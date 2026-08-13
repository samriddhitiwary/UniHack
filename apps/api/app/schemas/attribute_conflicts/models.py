"""Strict internal schemas for conflict-detection persistence boundaries."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_conflicts import (
    AttributeConflictType,
    AttributeConsensusStatus,
    ConflictDetectionResultStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class AttributeConflictSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CandidateAgreementGroupRecord(AttributeConflictSchema):
    group_id: str = Field(min_length=1, max_length=50)
    normalized_value: str = Field(min_length=1)
    normalized_unit: str | None
    candidate_ids: tuple[str, ...]
    distinct_source_ids: tuple[UUID, ...]
    candidate_count: int = Field(gt=0)
    distinct_source_count: int = Field(gt=0)


class AttributeConsensusRecord(AttributeConflictSchema):
    attribute_name: str = Field(min_length=1)
    attribute_display_name: str = Field(min_length=1)
    data_type: AttributeDataType
    status: AttributeConsensusStatus
    candidate_count: int = Field(gt=0)
    comparable_candidate_count: int = Field(ge=0)
    excluded_candidate_count: int = Field(ge=0)
    distinct_source_count: int = Field(gt=0)
    agreement_group_count: int = Field(ge=0)
    conflict_type: AttributeConflictType | None
    candidate_ids: tuple[str, ...]
    groups: tuple[CandidateAgreementGroupRecord, ...]
    consensus_confidence_bp: int = Field(ge=0, le=10_000)
    warning_codes: tuple[str, ...]


class AttributeConflictDetectionResultRecord(AttributeConflictSchema):
    conflict_detection_id: UUID
    job_id: UUID
    product_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    status: ConflictDetectionResultStatus
    attribute_count: int = Field(ge=0)
    agreement_count: int = Field(ge=0)
    tolerance_agreement_count: int = Field(ge=0)
    single_candidate_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    indeterminate_count: int = Field(ge=0)
    no_valid_candidate_count: int = Field(ge=0)
    attributes: tuple[AttributeConsensusRecord, ...]
    warning_codes: tuple[str, ...]
    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    created_at: AwareDatetime
