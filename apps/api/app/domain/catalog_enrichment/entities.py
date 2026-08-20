"""Immutable grounded catalog-enrichment domain models."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.catalog_enrichment.enums import ClaimRiskCode, EnrichmentWarningCode
from app.domain.catalog_projection import CatalogWarningReason
from app.domain.products import ProductCategory

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FACT_ID = re.compile(r"^(?:IDENTITY|ATTRIBUTE):[A-Za-z][A-Za-z0-9]*$")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("catalog enrichment timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class TrustedCatalogFact:
    fact_id: str
    display_name: str
    value: str
    unit: str | None = None
    origin: str | None = None
    validation_status: str | None = None

    def __post_init__(self) -> None:
        if (
            not _FACT_ID.fullmatch(self.fact_id)
            or not self.display_name.strip()
            or not self.value.strip()
        ):
            raise ValueError("trusted fact identity and value are required")
        if self.unit is not None and not self.unit.strip():
            raise ValueError("trusted fact unit must be nonblank when present")


@dataclass(frozen=True, slots=True, kw_only=True)
class TrustedCatalogFacts:
    product_id: UUID
    projection_id: UUID
    product_name: str
    manufacturer: str | None
    model_number: str | None
    category: ProductCategory
    description: str | None
    facts: tuple[TrustedCatalogFact, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    schema_version: int
    schema_fingerprint: str

    def __post_init__(self) -> None:
        if not self.product_name or self.schema_version < 1 or len(self.schema_fingerprint) != 64:
            raise ValueError("trusted catalog identity or schema lineage is invalid")
        if not self.facts or len({fact.fact_id for fact in self.facts}) != len(self.facts):
            raise ValueError("trusted facts must be nonempty and unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class GroundedGeneratedText:
    text: str
    fact_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.text.strip() or not self.fact_ids:
            raise ValueError("generated content text and grounding references are required")
        if len(set(self.fact_ids)) != len(self.fact_ids):
            raise ValueError("generated content fact references must be unique")
        if any(not _FACT_ID.fullmatch(fact_id) for fact_id in self.fact_ids):
            raise ValueError("generated content fact reference is invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class EnrichmentValidationResult:
    valid: bool
    issue_codes: tuple[ClaimRiskCode, ...]
    warning_codes: tuple[EnrichmentWarningCode, ...]
    grounded_fact_count: int
    referenced_fact_count: int

    def __post_init__(self) -> None:
        if self.valid == bool(self.issue_codes):
            raise ValueError("enrichment validation validity and issues are inconsistent")
        if self.grounded_fact_count < 0 or self.referenced_fact_count < 0:
            raise ValueError("enrichment validation counts cannot be negative")
        if len(set(self.issue_codes)) != len(self.issue_codes):
            raise ValueError("enrichment validation issue codes must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogEnrichmentResult:
    enrichment_id: UUID
    job_id: UUID
    product_id: UUID
    projection_id: UUID
    projection_product_version: int
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    title: GroundedGeneratedText
    description: GroundedGeneratedText
    feature_bullets: tuple[GroundedGeneratedText, ...]
    search_keywords: tuple[GroundedGeneratedText, ...]
    technical_summary: GroundedGeneratedText
    trusted_fact_count: int
    referenced_fact_count: int
    fact_coverage_bp: int
    grounding_score_bp: int
    warning_codes: tuple[EnrichmentWarningCode, ...]
    provider: str
    model: str
    prompt_version: str
    prompt_sha256: str
    generation_attempt_count: int
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        all_items = (
            self.title,
            self.description,
            *self.feature_bullets,
            *self.search_keywords,
            self.technical_summary,
        )
        referenced = {fact_id for item in all_items for fact_id in item.fact_ids}
        if self.projection_product_version < 1 or self.schema_version < 1:
            raise ValueError("catalog enrichment versions must be positive")
        if len(self.schema_fingerprint) != 64 or not _SHA256.fullmatch(self.prompt_sha256):
            raise ValueError("catalog enrichment hashes are invalid")
        if not 3 <= len(self.feature_bullets) <= 8 or not 1 <= len(self.search_keywords) <= 20:
            raise ValueError("catalog enrichment content counts are invalid")
        if (
            len(self.title.text) > 200
            or len(self.description.text) > 2_000
            or len(self.technical_summary.text) > 1_000
            or any(len(item.text) > 300 for item in self.feature_bullets)
            or any(len(item.text) > 100 for item in self.search_keywords)
            or any(len(item.fact_ids) > 50 for item in all_items)
            or sum(len(item.fact_ids) for item in all_items) > 500
        ):
            raise ValueError("catalog enrichment content exceeds domain safety limits")
        if any(
            len({" ".join(item.text.split()).casefold() for item in collection}) != len(collection)
            for collection in (self.feature_bullets, self.search_keywords)
        ):
            raise ValueError("catalog enrichment content must be unique")
        if self.trusted_fact_count < 1 or self.referenced_fact_count != len(referenced):
            raise ValueError("catalog enrichment fact counts are inconsistent")
        expected_coverage = self.referenced_fact_count * 10_000 // self.trusted_fact_count
        if self.fact_coverage_bp != expected_coverage or not 0 <= self.fact_coverage_bp <= 10_000:
            raise ValueError("catalog enrichment fact coverage is invalid")
        if self.grounding_score_bp != 10_000 or self.generation_attempt_count < 1:
            raise ValueError("catalog enrichment grounding or attempt metadata is invalid")
        if not all((self.provider.strip(), self.model.strip())):
            raise ValueError("catalog enrichment provider and model are required")
        if self.prompt_version != "catalog-enrichment-prompt-v1":
            raise ValueError("catalog enrichment prompt version is invalid")
        if self.engine != "grounded-commerce-content-generator-v1" or self.engine_version != "1.0":
            raise ValueError("catalog enrichment engine metadata is invalid")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("catalog enrichment warnings must be unique")
        object.__setattr__(self, "created_at", _utc(self.created_at))
