"""Strict internal schemas for immutable commerce catalog projections."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.domain.reviewed_attributes import FinalAttributeOrigin
from app.schemas.products.models import to_camel


class CatalogProjectionSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class CommerceCatalogAttributeRecord(CatalogProjectionSchema):
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    required: bool
    display_order: int = Field(gt=0)
    value: str
    unit: str | None
    origin: FinalAttributeOrigin
    review_decision_id: UUID
    candidate_id: str | None
    source_id: UUID | None
    validation_status: CandidateValidationStatus | None
    created_at: AwareDatetime


class CommerceCatalogProjectionRecord(CatalogProjectionSchema):
    projection_id: UUID
    job_id: UUID
    product_id: UUID
    product_version: int = Field(gt=0)
    materialization_id: UUID
    review_id: UUID
    selection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    conflict_detection_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int = Field(gt=0)
    schema_fingerprint: str = Field(min_length=64, max_length=64)
    product_name: str
    manufacturer: str | None
    model_number: str | None
    description: str | None
    status: CatalogProjectionStatus
    attribute_count: int = Field(ge=0)
    required_attribute_count: int = Field(ge=0)
    optional_attribute_count: int = Field(ge=0)
    unresolved_optional_count: int = Field(ge=0)
    blocking_reason_codes: tuple[CatalogBlockingReason, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    attributes: tuple[CommerceCatalogAttributeRecord, ...]
    engine: str
    engine_version: str
    created_at: AwareDatetime
