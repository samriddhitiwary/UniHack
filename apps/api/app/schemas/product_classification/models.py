"""Strict internal schemas for classification-result boundaries."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.product_classification import (
    ClassificationEvidenceType,
    ProductClassificationStatus,
)
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class ClassificationSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ClassificationMatchRecord(ClassificationSchema):
    match_id: str = Field(min_length=1, max_length=50)
    evidence_id: str = Field(min_length=1, max_length=50)
    source_id: UUID
    evidence_type: ClassificationEvidenceType
    category: ProductCategory
    matched_signal: str = Field(min_length=1, max_length=100)
    signal_strength: int = Field(ge=1, le=10)
    weighted_score: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=500)
    excerpt: str = Field(min_length=1, max_length=500)


class ProductClassificationResultRecord(ClassificationSchema):
    classification_id: UUID
    job_id: UUID
    product_id: UUID
    category: ProductCategory
    status: ProductClassificationStatus
    confidence_bp: int = Field(ge=0, le=10_000)
    pump_score: int = Field(ge=0)
    motor_score: int = Field(ge=0)
    evidence_item_count: int = Field(ge=0)
    matched_evidence_count: int = Field(ge=0)
    conflicting_evidence_count: int = Field(ge=0)
    matches: tuple[ClassificationMatchRecord, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: AwareDatetime
