"""Immutable, integer-only Product Intelligence Score models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.product_intelligence.enums import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceGrade,
)
from app.domain.products import ProductCategory


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductIntelligenceMetric:
    name: str
    value: int

    def __post_init__(self) -> None:
        if not self.name or isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValueError("intelligence metric must have a name and integer value")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductIntelligenceComponentScore:
    component: ProductIntelligenceComponent
    status: ComponentEvaluationStatus
    raw_score_bp: int | None
    base_weight_bp: int
    normalized_weight_bp: int
    weighted_contribution_bp: int
    strength_codes: tuple[str, ...]
    improvement_codes: tuple[str, ...]
    metrics: tuple[ProductIntelligenceMetric, ...]

    def __post_init__(self) -> None:
        if min(self.base_weight_bp, self.normalized_weight_bp, self.weighted_contribution_bp) < 0:
            raise ValueError("component weights and contribution cannot be negative")
        if (
            max(self.base_weight_bp, self.normalized_weight_bp, self.weighted_contribution_bp)
            > 10_000
        ):
            raise ValueError("component weights and contribution cannot exceed 10000")
        if self.status is ComponentEvaluationStatus.NOT_EVALUATED:
            if (
                self.raw_score_bp is not None
                or self.normalized_weight_bp
                or self.weighted_contribution_bp
            ):
                raise ValueError("not-evaluated components cannot contribute")
        elif self.raw_score_bp is None or not 0 <= self.raw_score_bp <= 10_000:
            raise ValueError("evaluated components require a bounded raw score")
        if len(set(self.strength_codes)) != len(self.strength_codes) or len(
            set(self.improvement_codes)
        ) != len(self.improvement_codes):
            raise ValueError("component reason codes must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductIntelligenceScoreResult:
    score_id: UUID
    job_id: UUID
    product_id: UUID
    projection_id: UUID
    materialization_id: UUID
    review_id: UUID
    selection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    conflict_detection_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    enrichment_id: UUID | None
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    projection_status: CatalogProjectionStatus
    overall_score_bp: int
    overall_score_percent: int
    grade: ProductIntelligenceGrade
    components: tuple[ProductIntelligenceComponentScore, ...]
    strength_codes: tuple[str, ...]
    improvement_codes: tuple[str, ...]
    top_improvement_codes: tuple[str, ...]
    metrics: tuple[ProductIntelligenceMetric, ...]
    policy_version: str
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.schema_version < 1 or len(self.schema_fingerprint) != 64:
            raise ValueError("score schema lineage is invalid")
        if not 0 <= self.overall_score_bp <= 10_000:
            raise ValueError("overall score is out of bounds")
        if self.overall_score_percent != (self.overall_score_bp + 50) // 100:
            raise ValueError("score percent is inconsistent")
        if tuple(item.component for item in self.components) != tuple(ProductIntelligenceComponent):
            raise ValueError("score requires all ordered components")
        if sum(item.normalized_weight_bp for item in self.components) != 10_000:
            raise ValueError("normalized component weights must sum to 10000")
        if sum(item.weighted_contribution_bp for item in self.components) != self.overall_score_bp:
            raise ValueError("component contributions must equal overall score")
        if len(self.top_improvement_codes) > 5:
            raise ValueError("top improvements exceed limit")
        if (
            len(self.strength_codes) + len(self.improvement_codes) > 100
            or len(self.metrics) > 100
            or any(
                len(item.strength_codes) + len(item.improvement_codes) > 100
                or len(item.metrics) > 100
                for item in self.components
            )
        ):
            raise ValueError("score reasons or metrics exceed limits")
        if any(
            len(set(values)) != len(values)
            for values in (self.strength_codes, self.improvement_codes, self.top_improvement_codes)
        ):
            raise ValueError("score reason codes must be unique")
        if self.policy_version != "product-intelligence-score-v1":
            raise ValueError("score policy version is invalid")
        if (
            self.engine != "deterministic-product-intelligence-scorer-v1"
            or self.engine_version != "1.0"
        ):
            raise ValueError("score engine metadata is invalid")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("score timestamp must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class ProductIntelligenceScorePage:
    items: tuple[ProductIntelligenceScoreResult, ...]
    next_cursor: str | None
