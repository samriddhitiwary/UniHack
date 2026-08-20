"""Immutable catalog search and dashboard summary models."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from app.domain.catalog_search.enums import CatalogSearchAccessPattern
from app.domain.product_intelligence import ProductIntelligenceGrade
from app.domain.products import ProductCategory, ProductStatus

_WHITESPACE = re.compile(r"\s+")


def normalize_catalog_search_text(value: str) -> str:
    """Trim, lowercase, and collapse whitespace without discarding punctuation."""
    return _WHITESPACE.sub(" ", value.strip().lower())


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogProductSearchQuery:
    limit: int = 20
    cursor: str | None = None
    category: ProductCategory | None = None
    status: ProductStatus | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    name_prefix: str | None = None
    publishing_readiness: CatalogProjectionStatus | None = None
    intelligence_grade: ProductIntelligenceGrade | None = None
    min_intelligence_score: int | None = None
    max_intelligence_score: int | None = None

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool) or not 1 <= self.limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        for field in ("manufacturer", "model_number", "name_prefix"):
            value = getattr(self, field)
            if value is not None:
                normalized = normalize_catalog_search_text(value)
                if not normalized or len(normalized) > 200:
                    raise ValueError(f"{field} must contain between 1 and 200 characters")
                object.__setattr__(self, field, normalized)
        for field in ("min_intelligence_score", "max_intelligence_score"):
            value = getattr(self, field)
            if value is not None and (isinstance(value, bool) or not 0 <= value <= 100):
                raise ValueError(f"{field} must be between 0 and 100")
        if (
            self.min_intelligence_score is not None
            and self.max_intelligence_score is not None
            and self.min_intelligence_score > self.max_intelligence_score
        ):
            raise ValueError("minimum intelligence score cannot exceed maximum")

    def plan(self) -> CatalogSearchAccessPattern | None:
        if any(
            value is not None
            for value in (
                self.publishing_readiness,
                self.intelligence_grade,
                self.min_intelligence_score,
                self.max_intelligence_score,
            )
        ):
            return None
        native = {
            "category": self.category,
            "status": self.status,
            "manufacturer": self.manufacturer,
            "model_number": self.model_number,
            "name_prefix": self.name_prefix,
        }
        active = tuple(name for name, value in native.items() if value is not None)
        plans = {
            (): CatalogSearchAccessPattern.CREATED_AT,
            ("status",): CatalogSearchAccessPattern.STATUS,
            ("category",): CatalogSearchAccessPattern.CATEGORY,
            ("category", "status"): CatalogSearchAccessPattern.CATEGORY_STATUS,
            ("manufacturer",): CatalogSearchAccessPattern.MANUFACTURER,
            ("model_number",): CatalogSearchAccessPattern.MODEL_NUMBER,
            ("name_prefix",): CatalogSearchAccessPattern.NAME_PREFIX,
        }
        return plans.get(active)


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogProjectionSummary:
    projection_id: UUID
    status: CatalogProjectionStatus
    product_version: int
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    blocking_reason_codes: tuple[CatalogBlockingReason, ...]
    created_at: datetime
    projection_current: bool
    eligible_for_ready_to_publish: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogIntelligenceSummary:
    score_id: UUID
    projection_id: UUID
    enrichment_id: UUID | None
    overall_score_bp: int
    overall_score_percent: int
    grade: ProductIntelligenceGrade
    top_improvement_codes: tuple[str, ...]
    strength_codes: tuple[str, ...]
    policy_version: str
    created_at: datetime
    intelligence_current: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogProductSummary:
    product_id: UUID
    name: str
    manufacturer: str | None
    model_number: str | None
    category: ProductCategory
    status: ProductStatus
    product_version: int
    created_at: datetime
    updated_at: datetime
    latest_projection: CatalogProjectionSummary | None
    latest_intelligence: CatalogIntelligenceSummary | None
    enrichment_available: bool
    export_available: bool


@dataclass(frozen=True, slots=True)
class CatalogProductSearchPage:
    items: tuple[CatalogProductSummary, ...]
    next_cursor: str | None
