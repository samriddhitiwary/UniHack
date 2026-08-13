"""Immutable agreement groups, attribute consensus, and result aggregate."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_conflicts.enums import (
    AttributeConflictType,
    AttributeConsensusStatus,
    ConflictDetectionResultStatus,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateAgreementGroup:
    group_id: str
    normalized_value: str
    normalized_unit: str | None
    candidate_ids: tuple[str, ...]
    distinct_source_ids: tuple[UUID, ...]
    candidate_count: int
    distinct_source_count: int

    def __post_init__(self) -> None:
        if not self.group_id or not self.normalized_value or not self.candidate_ids:
            raise ValueError("agreement group identity, value, and candidates are required")
        if self.candidate_count != len(self.candidate_ids) or self.distinct_source_count != len(
            self.distinct_source_ids
        ):
            raise ValueError("agreement group counts are inconsistent")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeConsensus:
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    status: AttributeConsensusStatus
    candidate_count: int
    comparable_candidate_count: int
    excluded_candidate_count: int
    distinct_source_count: int
    agreement_group_count: int
    conflict_type: AttributeConflictType | None
    candidate_ids: tuple[str, ...]
    groups: tuple[CandidateAgreementGroup, ...]
    consensus_confidence_bp: int
    warning_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.attribute_name or not self.attribute_display_name:
            raise ValueError("attribute consensus identity is required")
        if self.candidate_count != len(self.candidate_ids):
            raise ValueError("candidate_count must match candidate_ids")
        if self.comparable_candidate_count + self.excluded_candidate_count != self.candidate_count:
            raise ValueError("comparable and excluded counts must cover candidates")
        if self.agreement_group_count != len(self.groups):
            raise ValueError("agreement_group_count must match groups")
        if not 0 <= self.consensus_confidence_bp <= 10_000:
            raise ValueError("consensus confidence must be between 0 and 10000")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("warning codes must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeConflictDetectionResult:
    conflict_detection_id: UUID
    job_id: UUID
    product_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: ConflictDetectionResultStatus
    attribute_count: int
    agreement_count: int
    tolerance_agreement_count: int
    single_candidate_count: int
    conflict_count: int
    indeterminate_count: int
    no_valid_candidate_count: int
    attributes: tuple[AttributeConsensus, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        identities = (
            self.conflict_detection_id,
            self.job_id,
            self.product_id,
            self.normalization_id,
            self.extraction_id,
            self.classification_id,
        )
        if any(not isinstance(value, UUID) for value in identities):
            raise ValueError("conflict result identities must be UUIDs")
        expected = {
            AttributeConsensusStatus.AGREEMENT: self.agreement_count,
            AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE: self.tolerance_agreement_count,
            AttributeConsensusStatus.SINGLE_CANDIDATE: self.single_candidate_count,
            AttributeConsensusStatus.CONFLICT: self.conflict_count,
            AttributeConsensusStatus.INDETERMINATE: self.indeterminate_count,
            AttributeConsensusStatus.NO_VALID_CANDIDATES: self.no_valid_candidate_count,
        }
        if self.attribute_count != len(self.attributes) or any(
            count != sum(item.status is status for item in self.attributes)
            for status, count in expected.items()
        ):
            raise ValueError("conflict result counts are inconsistent")
        if len(set(self.warning_codes)) != len(self.warning_codes) or not self.engine:
            raise ValueError("result warnings or engine are invalid")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        normalization_id: UUID,
        extraction_id: UUID,
        classification_id: UUID,
        category: ProductCategory,
        schema_version: int,
        schema_fingerprint: str,
        attributes: tuple[AttributeConsensus, ...],
        now: datetime | None = None,
    ) -> "AttributeConflictDetectionResult":
        has_conflict = any(item.status is AttributeConsensusStatus.CONFLICT for item in attributes)
        has_warning = any(
            item.status
            in {
                AttributeConsensusStatus.INDETERMINATE,
                AttributeConsensusStatus.NO_VALID_CANDIDATES,
            }
            or item.warning_codes
            for item in attributes
        )
        has_comparison = any(
            item.status
            in {
                AttributeConsensusStatus.AGREEMENT,
                AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE,
                AttributeConsensusStatus.CONFLICT,
            }
            for item in attributes
        )
        status = (
            ConflictDetectionResultStatus.CONFLICTS_FOUND
            if has_conflict
            else ConflictDetectionResultStatus.COMPLETED_WITH_WARNINGS
            if has_warning
            else ConflictDetectionResultStatus.NO_CONFLICTS
            if has_comparison
            else ConflictDetectionResultStatus.NO_COMPARABLE_ATTRIBUTES
        )
        return cls(
            conflict_detection_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            normalization_id=normalization_id,
            extraction_id=extraction_id,
            classification_id=classification_id,
            category=category,
            schema_version=schema_version,
            schema_fingerprint=schema_fingerprint,
            status=status,
            attribute_count=len(attributes),
            agreement_count=sum(
                item.status is AttributeConsensusStatus.AGREEMENT for item in attributes
            ),
            tolerance_agreement_count=sum(
                item.status is AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE
                for item in attributes
            ),
            single_candidate_count=sum(
                item.status is AttributeConsensusStatus.SINGLE_CANDIDATE for item in attributes
            ),
            conflict_count=sum(
                item.status is AttributeConsensusStatus.CONFLICT for item in attributes
            ),
            indeterminate_count=sum(
                item.status is AttributeConsensusStatus.INDETERMINATE for item in attributes
            ),
            no_valid_candidate_count=sum(
                item.status is AttributeConsensusStatus.NO_VALID_CANDIDATES for item in attributes
            ),
            attributes=attributes,
            warning_codes=tuple(
                dict.fromkeys(code for item in attributes for code in item.warning_codes)
            ),
            engine="deterministic-conflict-detector-v1",
            engine_version="1.0",
            created_at=now or datetime.now(UTC),
        )
