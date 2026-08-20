"""Validated catalog search request model."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.product_intelligence import ProductIntelligenceGrade
from app.domain.products import ProductCategory, ProductStatus
from app.schemas.products.models import to_camel


class CatalogProductSearchRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, min_length=1, max_length=4_096)
    category: ProductCategory | None = None
    status: ProductStatus | None = None
    manufacturer: str | None = Field(default=None, min_length=1, max_length=200)
    model_number: str | None = Field(default=None, min_length=1, max_length=200)
    name_prefix: str | None = Field(default=None, min_length=1, max_length=200)
    publishing_readiness: CatalogProjectionStatus | None = None
    intelligence_grade: ProductIntelligenceGrade | None = None
    min_intelligence_score: int | None = Field(default=None, ge=0, le=100)
    max_intelligence_score: int | None = Field(default=None, ge=0, le=100)
