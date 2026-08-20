"""Compact catalog search and single-Product summary responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from app.domain.catalog_search import CatalogProductSummary
from app.domain.product_intelligence import ProductIntelligenceGrade
from app.domain.products import ProductCategory, ProductStatus
from app.schemas.products.models import to_camel


class CatalogSearchSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class LatestProjectionSummaryResponse(CatalogSearchSchema):
    projection_id: UUID
    status: CatalogProjectionStatus
    product_version: int
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    blocking_reason_codes: tuple[CatalogBlockingReason, ...]
    created_at: datetime
    projection_current: bool
    eligible_for_ready_to_publish: bool


class LatestIntelligenceSummaryResponse(CatalogSearchSchema):
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


class CatalogProductSearchItemResponse(CatalogSearchSchema):
    product_id: UUID
    name: str
    manufacturer: str | None
    model_number: str | None
    category: ProductCategory
    status: ProductStatus
    product_version: int
    created_at: datetime
    updated_at: datetime
    projection_id: UUID | None
    publishing_readiness: CatalogProjectionStatus | None
    projection_current: bool | None
    intelligence_score_id: UUID | None
    intelligence_score_percent: int | None
    intelligence_grade: ProductIntelligenceGrade | None
    intelligence_current: bool | None
    top_improvement_codes: tuple[str, ...]
    enrichment_available: bool
    export_available: bool

    @classmethod
    def from_summary(cls, value: CatalogProductSummary) -> "CatalogProductSearchItemResponse":
        projection = value.latest_projection
        intelligence = value.latest_intelligence
        return cls(
            product_id=value.product_id,
            name=value.name,
            manufacturer=value.manufacturer,
            model_number=value.model_number,
            category=value.category,
            status=value.status,
            product_version=value.product_version,
            created_at=value.created_at,
            updated_at=value.updated_at,
            projection_id=projection.projection_id if projection else None,
            publishing_readiness=projection.status if projection else None,
            projection_current=projection.projection_current if projection else None,
            intelligence_score_id=intelligence.score_id if intelligence else None,
            intelligence_score_percent=(
                intelligence.overall_score_percent if intelligence else None
            ),
            intelligence_grade=intelligence.grade if intelligence else None,
            intelligence_current=(intelligence.intelligence_current if intelligence else None),
            top_improvement_codes=(intelligence.top_improvement_codes if intelligence else ()),
            enrichment_available=value.enrichment_available,
            export_available=value.export_available,
        )


class CatalogProductSearchResponse(CatalogSearchSchema):
    items: tuple[CatalogProductSearchItemResponse, ...]
    next_cursor: str | None


class CatalogProductSummaryResponse(CatalogSearchSchema):
    product_id: UUID
    name: str
    manufacturer: str | None
    model_number: str | None
    category: ProductCategory
    status: ProductStatus
    version: int
    created_at: datetime
    updated_at: datetime
    latest_projection: LatestProjectionSummaryResponse | None
    latest_intelligence: LatestIntelligenceSummaryResponse | None
    enrichment_available: bool
    export_available: bool

    @classmethod
    def from_summary(cls, value: CatalogProductSummary) -> "CatalogProductSummaryResponse":
        return cls(
            product_id=value.product_id,
            name=value.name,
            manufacturer=value.manufacturer,
            model_number=value.model_number,
            category=value.category,
            status=value.status,
            version=value.product_version,
            created_at=value.created_at,
            updated_at=value.updated_at,
            latest_projection=(
                LatestProjectionSummaryResponse.model_validate(value.latest_projection)
                if value.latest_projection
                else None
            ),
            latest_intelligence=(
                LatestIntelligenceSummaryResponse.model_validate(value.latest_intelligence)
                if value.latest_intelligence
                else None
            ),
            enrichment_available=value.enrichment_available,
            export_available=value.export_available,
        )
