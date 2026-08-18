"""Camel-case product-review API responses."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.product_review import AttributeReviewDecisionType, ProductReviewSessionStatus
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class ReviewResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class ProductReviewRecord(ReviewResponse):
    review_id: UUID
    product_id: UUID
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
    status: ProductReviewSessionStatus
    version: int = Field(gt=0)
    required_attribute_count: int = Field(ge=0)
    required_resolved_count: int = Field(ge=0)
    required_unresolved_count: int = Field(ge=0)
    optional_attribute_count: int = Field(ge=0)
    optional_resolved_count: int = Field(ge=0)
    decision_count: int = Field(ge=0)
    completion_ready: bool
    created_at: AwareDatetime
    updated_at: AwareDatetime
    completed_at: AwareDatetime | None


class AttributeReviewDecisionRecord(ReviewResponse):
    decision_id: UUID
    review_id: UUID
    product_id: UUID
    decision_sequence: int = Field(gt=0)
    attribute_name: str
    decision_type: AttributeReviewDecisionType
    candidate_id: str | None
    approved_value: str | None
    approved_unit: str | None
    manual_raw_value: str | None
    manual_raw_unit: str | None
    comment: str | None
    reviewer_id: str
    review_version: int = Field(gt=0)
    created_at: AwareDatetime


class ReviewDecisionListResult(ReviewResponse):
    items: tuple[AttributeReviewDecisionRecord, ...]
    next_cursor: str | None = None
