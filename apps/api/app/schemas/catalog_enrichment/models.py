"""Serializable catalog enrichment result records."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.catalog_enrichment import EnrichmentWarningCode
from app.domain.products import ProductCategory
from app.schemas.products.models import to_camel


class GroundedGeneratedTextRecord(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    text: str
    fact_ids: tuple[str, ...]


class CatalogEnrichmentResultRecord(BaseModel):
    model_config = GroundedGeneratedTextRecord.model_config

    enrichment_id: UUID
    job_id: UUID
    product_id: UUID
    projection_id: UUID
    projection_product_version: int
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    title: GroundedGeneratedTextRecord
    description: GroundedGeneratedTextRecord
    feature_bullets: tuple[GroundedGeneratedTextRecord, ...]
    search_keywords: tuple[GroundedGeneratedTextRecord, ...]
    technical_summary: GroundedGeneratedTextRecord
    trusted_fact_count: int
    referenced_fact_count: int
    fact_coverage_bp: int = Field(ge=0, le=10_000)
    grounding_score_bp: int = Field(ge=0, le=10_000)
    warning_codes: tuple[EnrichmentWarningCode, ...]
    provider: str
    model: str
    prompt_version: str
    prompt_sha256: str
    generation_attempt_count: int
    engine: str
    engine_version: str
    created_at: AwareDatetime
