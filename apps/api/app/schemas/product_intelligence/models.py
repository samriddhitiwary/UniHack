"""Read-safe Product Intelligence Score schema models for future API use."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceGrade,
)


class ProductIntelligenceMetricRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    value: int


class ProductIntelligenceComponentRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    component: ProductIntelligenceComponent
    status: ComponentEvaluationStatus
    raw_score_bp: int | None
    base_weight_bp: int
    normalized_weight_bp: int
    weighted_contribution_bp: int
    strength_codes: tuple[str, ...]
    improvement_codes: tuple[str, ...]
    metrics: tuple[ProductIntelligenceMetricRecord, ...]


class ProductIntelligenceScoreRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    score_id: UUID
    job_id: UUID
    product_id: UUID
    projection_id: UUID
    enrichment_id: UUID | None
    projection_status: CatalogProjectionStatus
    overall_score_bp: int
    overall_score_percent: int
    grade: ProductIntelligenceGrade
    components: tuple[ProductIntelligenceComponentRecord, ...]
    strength_codes: tuple[str, ...]
    improvement_codes: tuple[str, ...]
    top_improvement_codes: tuple[str, ...]
    policy_version: str
    created_at: datetime
