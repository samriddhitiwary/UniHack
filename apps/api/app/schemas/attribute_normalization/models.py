"""Strict internal schemas for attribute normalization boundaries."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.attribute_normalization import (
    AttributeNormalizationResultStatus,
    NormalizationStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class AttributeNormalizationSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class NormalizedAttributeCandidateRecord(AttributeNormalizationSchema):
    normalized_candidate_id: str = Field(min_length=1, max_length=50)
    source_candidate_id: str = Field(min_length=1, max_length=50)
    source_extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    raw_value: str | None
    raw_unit: str | None
    normalized_value: str | None
    normalized_unit: str | None
    normalization_status: NormalizationStatus
    conversion_applied: bool
    unit_canonicalization_applied: bool
    conversion_rule: str | None
    source_id: UUID
    evidence_type: AttributeExtractionEvidenceType
    evidence_location: str
    evidence_excerpt: str = Field(min_length=1, max_length=1_000)
    extraction_confidence_bp: int = Field(ge=0, le=10_000)
    normalization_confidence_bp: int = Field(ge=0, le=10_000)
    created_at: AwareDatetime


class AttributeNormalizationResultRecord(AttributeNormalizationSchema):
    normalization_id: UUID
    job_id: UUID
    product_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    status: AttributeNormalizationResultStatus
    candidate_count: int = Field(ge=0)
    normalized_count: int = Field(ge=0)
    converted_count: int = Field(ge=0)
    unit_missing_count: int = Field(ge=0)
    unsupported_unit_count: int = Field(ge=0)
    invalid_value_count: int = Field(ge=0)
    candidates: tuple[NormalizedAttributeCandidateRecord, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: AwareDatetime
