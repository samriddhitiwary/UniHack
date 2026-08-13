"""Immutable evidence, candidates, and traceable extraction results."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_extraction.enums import (
    AttributeExtractionEvidenceType,
    AttributeMatchType,
    AttributeValueParseStatus,
    StructuredAttributeExtractionStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeExtractionEvidence:
    evidence_id: str
    source_id: UUID
    evidence_type: AttributeExtractionEvidenceType
    text: str
    location: str
    source_quality_bp: int
    order: int
    label_hint: str | None = None
    value_hint: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.text or not self.location:
            raise ValueError("evidence identity, text, and location are required")
        if not isinstance(self.source_id, UUID) or not isinstance(
            self.evidence_type, AttributeExtractionEvidenceType
        ):
            raise ValueError("evidence source or type is invalid")
        if not 0 <= self.source_quality_bp <= 10_000 or self.order < 0:
            raise ValueError("evidence quality or order is invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeCandidate:
    candidate_id: str
    attribute_name: str
    attribute_display_name: str
    attribute_data_type: AttributeDataType
    raw_value: str | None
    raw_unit: str | None
    source_id: UUID
    evidence_id: str
    evidence_type: AttributeExtractionEvidenceType
    location: str
    excerpt: str
    matched_label: str
    match_type: AttributeMatchType
    confidence_bp: int
    source_quality_bp: int
    parse_status: AttributeValueParseStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.attribute_name or not self.matched_label:
            raise ValueError("candidate identity, attribute, and label are required")
        if not self.location or not self.excerpt or len(self.excerpt) > 1_000:
            raise ValueError("candidate excerpt must be nonempty and bounded")
        if not 0 <= self.confidence_bp <= 10_000 or not 0 <= self.source_quality_bp <= 10_000:
            raise ValueError("candidate confidence is invalid")
        if self.parse_status is AttributeValueParseStatus.MISSING_VALUE:
            if self.raw_value is not None:
                raise ValueError("missing values cannot carry raw_value")
        elif not self.raw_value:
            raise ValueError("non-missing candidates require raw_value")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class StructuredAttributeExtractionResult:
    extraction_id: UUID
    job_id: UUID
    product_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: StructuredAttributeExtractionStatus
    evidence_item_count: int
    candidate_count: int
    distinct_attribute_count: int
    duplicate_count: int
    candidates: tuple[AttributeCandidate, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (self.extraction_id, self.job_id, self.product_id, self.classification_id)
        ):
            raise ValueError("result identities must be UUIDs")
        if (
            self.candidate_count != len(self.candidates)
            or self.distinct_attribute_count
            != len({candidate.attribute_name for candidate in self.candidates})
            or min(
                self.evidence_item_count,
                self.candidate_count,
                self.distinct_attribute_count,
                self.duplicate_count,
            )
            < 0
        ):
            raise ValueError("result counts are inconsistent")
        if self.status is StructuredAttributeExtractionStatus.NO_CANDIDATES and self.candidates:
            raise ValueError("NO_CANDIDATES cannot contain candidates")
        if (
            not self.engine
            or not self.engine_version
            or len(set(self.warning_codes)) != len(self.warning_codes)
        ):
            raise ValueError("result engine or warnings are invalid")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        classification_id: UUID,
        category: ProductCategory,
        schema_version: int,
        schema_fingerprint: str,
        evidence_item_count: int,
        candidates: tuple[AttributeCandidate, ...],
        duplicate_count: int,
        warning_codes: tuple[str, ...],
        now: datetime | None = None,
    ) -> "StructuredAttributeExtractionResult":
        status = (
            StructuredAttributeExtractionStatus.NO_CANDIDATES
            if not candidates
            else StructuredAttributeExtractionStatus.CANDIDATES_WITH_WARNINGS
            if warning_codes
            else StructuredAttributeExtractionStatus.CANDIDATES_FOUND
        )
        return cls(
            extraction_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            classification_id=classification_id,
            category=category,
            schema_version=schema_version,
            schema_fingerprint=schema_fingerprint,
            status=status,
            evidence_item_count=evidence_item_count,
            candidate_count=len(candidates),
            distinct_attribute_count=len({candidate.attribute_name for candidate in candidates}),
            duplicate_count=duplicate_count,
            candidates=candidates,
            warning_codes=warning_codes,
            engine="deterministic-schema-extractor-v1",
            engine_version="1.0",
            created_at=now or datetime.now(UTC),
        )
