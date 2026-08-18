"""Strict internal schemas for attribute validation boundaries."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.attribute_validation import (
    AttributeValidationResultStatus,
    CandidateValidationStatus,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class AttributeValidationSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class AttributeValidationIssueRecord(AttributeValidationSchema):
    issue_id: str = Field(min_length=1, max_length=100)
    issue_type: ValidationIssueType
    severity: ValidationIssueSeverity
    message_code: str = Field(min_length=1, max_length=100)
    expected: str | None = Field(default=None, max_length=10_000)
    actual: str | None = Field(default=None, max_length=10_000)


class CandidateValidationAssessmentRecord(AttributeValidationSchema):
    assessment_id: UUID
    normalized_candidate_id: str = Field(min_length=1)
    source_candidate_id: str = Field(min_length=1)
    attribute_name: str = Field(min_length=1)
    attribute_display_name: str = Field(min_length=1)
    data_type: AttributeDataType
    status: CandidateValidationStatus
    normalized_value: str | None
    normalized_unit: str | None
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    issues: tuple[AttributeValidationIssueRecord, ...]
    source_id: UUID
    evidence_type: AttributeExtractionEvidenceType
    evidence_location: str = Field(min_length=1)
    created_at: AwareDatetime


class AttributeValidationSummaryRecord(AttributeValidationSchema):
    attribute_name: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)
    valid_candidate_count: int = Field(ge=0)
    valid_with_warnings_candidate_count: int = Field(ge=0)
    invalid_candidate_count: int = Field(ge=0)
    not_validatable_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)


class AttributeValidationResultRecord(AttributeValidationSchema):
    validation_id: UUID
    job_id: UUID
    product_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    status: AttributeValidationResultStatus
    candidate_count: int = Field(ge=0)
    valid_count: int = Field(ge=0)
    valid_with_warnings_count: int = Field(ge=0)
    invalid_count: int = Field(ge=0)
    not_validatable_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    attribute_summary_count: int = Field(ge=0)
    assessments: tuple[CandidateValidationAssessmentRecord, ...]
    attribute_summaries: tuple[AttributeValidationSummaryRecord, ...]
    warning_codes: tuple[str, ...]
    engine: str = Field(min_length=1)
    engine_version: str = Field(min_length=1)
    created_at: AwareDatetime
