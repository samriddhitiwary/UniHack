"""Public Product Intelligence Score detail and history responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceGrade,
    ProductIntelligenceScoreResult,
)
from app.schemas.products.models import to_camel


class ProductIntelligenceReadSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class ProductIntelligenceMetricResponse(ProductIntelligenceReadSchema):
    name: str
    value: int


class ProductIntelligenceComponentResponse(ProductIntelligenceReadSchema):
    component: ProductIntelligenceComponent
    status: ComponentEvaluationStatus
    raw_score_bp: int | None
    base_weight_bp: int
    normalized_weight_bp: int
    weighted_contribution_bp: int
    strength_codes: tuple[str, ...]
    improvement_codes: tuple[str, ...]
    metrics: tuple[ProductIntelligenceMetricResponse, ...]


class ProductIntelligenceScoreDetailResponse(ProductIntelligenceReadSchema):
    score_id: UUID
    product_id: UUID
    projection_id: UUID
    enrichment_id: UUID | None
    overall_score_bp: int
    overall_score_percent: int
    grade: ProductIntelligenceGrade
    projection_status: CatalogProjectionStatus
    components: tuple[ProductIntelligenceComponentResponse, ...]
    strength_codes: tuple[str, ...]
    improvement_codes: tuple[str, ...]
    top_improvement_codes: tuple[str, ...]
    metrics: tuple[ProductIntelligenceMetricResponse, ...]
    policy_version: str
    created_at: datetime


class ProductIntelligenceScoreHistoryItemResponse(ProductIntelligenceReadSchema):
    score_id: UUID
    overall_score_bp: int
    overall_score_percent: int
    grade: ProductIntelligenceGrade
    projection_id: UUID
    enrichment_id: UUID | None
    policy_version: str
    created_at: datetime

    @classmethod
    def from_result(
        cls, result: ProductIntelligenceScoreResult
    ) -> "ProductIntelligenceScoreHistoryItemResponse":
        return cls.model_validate(result)


class ProductIntelligenceScoreHistoryResponse(ProductIntelligenceReadSchema):
    items: tuple[ProductIntelligenceScoreHistoryItemResponse, ...]
    next_cursor: str | None
