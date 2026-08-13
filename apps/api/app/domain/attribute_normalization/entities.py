"""Immutable normalized candidates and result aggregates."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.attribute_normalization.enums import (
    AttributeNormalizationResultStatus,
    NormalizationStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory


@dataclass(frozen=True, slots=True, kw_only=True)
class NormalizedAttributeCandidate:
    normalized_candidate_id: str
    source_candidate_id: str
    source_extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    raw_value: str | None
    raw_unit: str | None
    normalized_value: str | None
    normalized_unit: str | None
    normalization_status: NormalizationStatus
    conversion_applied: bool
    unit_canonicalization_applied: bool
    conversion_rule: str | None
    source_id: UUID
    evidence_type: AttributeExtractionEvidenceType
    evidence_location: str
    evidence_excerpt: str
    extraction_confidence_bp: int
    normalization_confidence_bp: int
    created_at: datetime

    def __post_init__(self) -> None:
        if (
            not self.normalized_candidate_id
            or not self.source_candidate_id
            or not self.attribute_name
        ):
            raise ValueError("normalized candidate identity and attribute are required")
        if any(
            not isinstance(value, UUID)
            for value in (self.source_extraction_id, self.classification_id, self.source_id)
        ):
            raise ValueError("normalized candidate lineage identities must be UUIDs")
        if (
            not 0 <= self.extraction_confidence_bp <= 10_000
            or not 0 <= self.normalization_confidence_bp <= 10_000
        ):
            raise ValueError("candidate confidence must be between 0 and 10000")
        if (
            not self.evidence_location
            or not self.evidence_excerpt
            or len(self.evidence_excerpt) > 1_000
        ):
            raise ValueError("candidate evidence must be nonempty and bounded")
        if self.conversion_applied is (self.conversion_rule is None):
            raise ValueError("conversion metadata is inconsistent")
        if (
            self.normalization_status is NormalizationStatus.NORMALIZED_WITH_CONVERSION
            and not self.conversion_applied
        ):
            raise ValueError("converted status requires conversion metadata")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeNormalizationResult:
    normalization_id: UUID
    job_id: UUID
    product_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: AttributeNormalizationResultStatus
    candidate_count: int
    normalized_count: int
    converted_count: int
    unit_missing_count: int
    unsupported_unit_count: int
    invalid_value_count: int
    candidates: tuple[NormalizedAttributeCandidate, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (
                self.normalization_id,
                self.job_id,
                self.product_id,
                self.extraction_id,
                self.classification_id,
            )
        ):
            raise ValueError("normalization result identities must be UUIDs")
        counts = {
            NormalizationStatus.NORMALIZED: self.normalized_count,
            NormalizationStatus.NORMALIZED_WITH_CONVERSION: self.converted_count,
            NormalizationStatus.UNIT_MISSING: self.unit_missing_count,
            NormalizationStatus.UNSUPPORTED_UNIT: self.unsupported_unit_count,
            NormalizationStatus.INVALID_VALUE: self.invalid_value_count,
        }
        if self.candidate_count != len(self.candidates) or any(
            expected != sum(item.normalization_status is status for item in self.candidates)
            for status, expected in counts.items()
        ):
            raise ValueError("normalization result counts are inconsistent")
        if self.status is AttributeNormalizationResultStatus.NO_CANDIDATES and self.candidates:
            raise ValueError("NO_CANDIDATES cannot contain candidates")
        if (
            len(set(self.warning_codes)) != len(self.warning_codes)
            or not self.engine
            or not self.engine_version
        ):
            raise ValueError("normalization result warnings or engine are invalid")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        extraction_id: UUID,
        classification_id: UUID,
        category: ProductCategory,
        schema_version: int,
        schema_fingerprint: str,
        candidates: tuple[NormalizedAttributeCandidate, ...],
        now: datetime | None = None,
    ) -> "AttributeNormalizationResult":
        warnings = tuple(
            status.value
            for status in (
                NormalizationStatus.UNIT_MISSING,
                NormalizationStatus.UNSUPPORTED_UNIT,
                NormalizationStatus.INVALID_VALUE,
            )
            if any(item.normalization_status is status for item in candidates)
        )
        status = (
            AttributeNormalizationResultStatus.NO_CANDIDATES
            if not candidates
            else AttributeNormalizationResultStatus.NORMALIZED_WITH_WARNINGS
            if warnings
            else AttributeNormalizationResultStatus.NORMALIZED
        )
        return cls(
            normalization_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            extraction_id=extraction_id,
            classification_id=classification_id,
            category=category,
            schema_version=schema_version,
            schema_fingerprint=schema_fingerprint,
            status=status,
            candidate_count=len(candidates),
            normalized_count=sum(
                item.normalization_status is NormalizationStatus.NORMALIZED for item in candidates
            ),
            converted_count=sum(
                item.normalization_status is NormalizationStatus.NORMALIZED_WITH_CONVERSION
                for item in candidates
            ),
            unit_missing_count=sum(
                item.normalization_status is NormalizationStatus.UNIT_MISSING for item in candidates
            ),
            unsupported_unit_count=sum(
                item.normalization_status is NormalizationStatus.UNSUPPORTED_UNIT
                for item in candidates
            ),
            invalid_value_count=sum(
                item.normalization_status is NormalizationStatus.INVALID_VALUE
                for item in candidates
            ),
            candidates=candidates,
            warning_codes=warnings,
            engine="deterministic-attribute-normalizer-v1",
            engine_version="1.0",
            created_at=now or datetime.now(UTC),
        )
