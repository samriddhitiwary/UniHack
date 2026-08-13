"""Immutable per-attribute completeness assessments and aggregate result."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_completeness.enums import (
    AttributeCompletenessState,
    AttributeCompletenessStatus,
)
from app.domain.attribute_conflicts import (
    AttributeConflictType,
    AttributeConsensusStatus,
)
from app.domain.products import ProductCategory


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeCompletenessAssessment:
    attribute_name: str
    attribute_display_name: str
    required: bool
    display_order: int
    state: AttributeCompletenessState
    candidate_count: int
    comparable_candidate_count: int
    distinct_source_count: int
    consensus_status: AttributeConsensusStatus | None
    consensus_confidence_bp: int | None
    conflict_type: AttributeConflictType | None
    available: bool
    resolved: bool
    verified: bool
    candidate_ids: tuple[str, ...]
    warning_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.attribute_name or not self.attribute_display_name or self.display_order < 1:
            raise ValueError("attribute completeness identity is invalid")
        if self.candidate_count != len(self.candidate_ids):
            raise ValueError("candidate_count must match candidate_ids")
        if not 0 <= self.comparable_candidate_count <= self.candidate_count:
            raise ValueError("comparable candidate count is invalid")
        if not 0 <= self.distinct_source_count <= self.candidate_count:
            raise ValueError("distinct source count is invalid")
        if self.consensus_confidence_bp is not None and not (
            0 <= self.consensus_confidence_bp <= 10_000
        ):
            raise ValueError("consensus confidence must be between 0 and 10000")
        expected = state_flags(self.state)
        if (self.available, self.resolved, self.verified) != expected:
            raise ValueError("completeness state flags are inconsistent")
        if self.state is AttributeCompletenessState.MISSING and (
            self.consensus_status is not None or self.candidate_ids
        ):
            raise ValueError("missing assessments cannot carry candidate consensus")
        if self.state is not AttributeCompletenessState.MISSING and self.consensus_status is None:
            raise ValueError("non-missing assessments require consensus lineage")
        if len(set(self.warning_codes)) != len(self.warning_codes):
            raise ValueError("warning codes must be unique")


def state_flags(state: AttributeCompletenessState) -> tuple[bool, bool, bool]:
    available = state not in {
        AttributeCompletenessState.INVALID_ONLY,
        AttributeCompletenessState.MISSING,
    }
    resolved = state in {
        AttributeCompletenessState.PRESENT,
        AttributeCompletenessState.PRESENT_WITH_TOLERANCE,
        AttributeCompletenessState.PRESENT_SINGLE_SOURCE,
    }
    verified = state in {
        AttributeCompletenessState.PRESENT,
        AttributeCompletenessState.PRESENT_WITH_TOLERANCE,
    }
    return available, resolved, verified


def percentage_basis_points(count: int, total: int) -> int:
    if count < 0 or total < 0 or count > total:
        raise ValueError("percentage counts are invalid")
    return 10_000 if total == 0 else count * 10_000 // total


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeCompletenessResult:
    completeness_id: UUID
    job_id: UUID
    product_id: UUID
    conflict_detection_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: AttributeCompletenessStatus
    required_attribute_count: int
    required_available_count: int
    required_resolved_count: int
    required_verified_count: int
    required_missing_count: int
    required_conflicted_count: int
    required_indeterminate_count: int
    required_invalid_count: int
    optional_attribute_count: int
    optional_available_count: int
    optional_resolved_count: int
    optional_verified_count: int
    optional_missing_count: int
    optional_conflicted_count: int
    optional_indeterminate_count: int
    optional_invalid_count: int
    total_attribute_count: int
    total_available_count: int
    total_resolved_count: int
    total_verified_count: int
    total_missing_count: int
    total_conflicted_count: int
    total_indeterminate_count: int
    total_invalid_count: int
    required_available_bp: int
    required_resolved_bp: int
    required_verified_bp: int
    overall_available_bp: int
    overall_resolved_bp: int
    attributes: tuple[AttributeCompletenessAssessment, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        identities = (
            self.completeness_id,
            self.job_id,
            self.product_id,
            self.conflict_detection_id,
            self.normalization_id,
            self.extraction_id,
            self.classification_id,
        )
        if any(not isinstance(value, UUID) for value in identities):
            raise ValueError("completeness lineage identities must be UUIDs")
        required = tuple(item for item in self.attributes if item.required)
        optional = tuple(item for item in self.attributes if not item.required)
        self._validate_counts("required", required)
        self._validate_counts("optional", optional)
        self._validate_counts("total", self.attributes)
        expected_bp = (
            percentage_basis_points(self.required_available_count, self.required_attribute_count),
            percentage_basis_points(self.required_resolved_count, self.required_attribute_count),
            percentage_basis_points(self.required_verified_count, self.required_attribute_count),
            percentage_basis_points(self.total_available_count, self.total_attribute_count),
            percentage_basis_points(self.total_resolved_count, self.total_attribute_count),
        )
        actual_bp = (
            self.required_available_bp,
            self.required_resolved_bp,
            self.required_verified_bp,
            self.overall_available_bp,
            self.overall_resolved_bp,
        )
        if actual_bp != expected_bp:
            raise ValueError("completeness percentages are inconsistent")
        if tuple(sorted(self.attributes, key=lambda item: item.display_order)) != self.attributes:
            raise ValueError("attributes must follow schema display order")
        if len(set(self.warning_codes)) != len(self.warning_codes) or not self.engine:
            raise ValueError("result warnings or engine are invalid")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    def _validate_counts(
        self, prefix: str, items: tuple[AttributeCompletenessAssessment, ...]
    ) -> None:
        expected = {
            "attribute_count": len(items),
            "available_count": sum(item.available for item in items),
            "resolved_count": sum(item.resolved for item in items),
            "verified_count": sum(item.verified for item in items),
            "missing_count": sum(
                item.state is AttributeCompletenessState.MISSING for item in items
            ),
            "conflicted_count": sum(
                item.state is AttributeCompletenessState.CONFLICTED for item in items
            ),
            "indeterminate_count": sum(
                item.state is AttributeCompletenessState.INDETERMINATE for item in items
            ),
            "invalid_count": sum(
                item.state is AttributeCompletenessState.INVALID_ONLY for item in items
            ),
        }
        if any(getattr(self, f"{prefix}_{name}") != value for name, value in expected.items()):
            raise ValueError(f"{prefix} completeness counts are inconsistent")

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        conflict_detection_id: UUID,
        normalization_id: UUID,
        extraction_id: UUID,
        classification_id: UUID,
        category: ProductCategory,
        schema_version: int,
        schema_fingerprint: str,
        attributes: tuple[AttributeCompletenessAssessment, ...],
        now: datetime | None = None,
    ) -> "AttributeCompletenessResult":
        required = tuple(item for item in attributes if item.required)
        optional = tuple(item for item in attributes if not item.required)
        status = completeness_status(required, attributes)
        values: dict[str, object] = {}
        for prefix, items in (
            ("required", required),
            ("optional", optional),
            ("total", attributes),
        ):
            values.update(_counts(prefix, items))
        return cls(
            completeness_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            conflict_detection_id=conflict_detection_id,
            normalization_id=normalization_id,
            extraction_id=extraction_id,
            classification_id=classification_id,
            category=category,
            schema_version=schema_version,
            schema_fingerprint=schema_fingerprint,
            status=status,
            **values,  # type: ignore[arg-type]
            required_available_bp=percentage_basis_points(
                sum(item.available for item in required), len(required)
            ),
            required_resolved_bp=percentage_basis_points(
                sum(item.resolved for item in required), len(required)
            ),
            required_verified_bp=percentage_basis_points(
                sum(item.verified for item in required), len(required)
            ),
            overall_available_bp=percentage_basis_points(
                sum(item.available for item in attributes), len(attributes)
            ),
            overall_resolved_bp=percentage_basis_points(
                sum(item.resolved for item in attributes), len(attributes)
            ),
            attributes=attributes,
            warning_codes=tuple(
                dict.fromkeys(code for item in attributes for code in item.warning_codes)
            ),
            engine="deterministic-completeness-engine-v1",
            engine_version="1.0",
            created_at=now or datetime.now(UTC),
        )


def _counts(prefix: str, items: tuple[AttributeCompletenessAssessment, ...]) -> dict[str, int]:
    return {
        f"{prefix}_attribute_count": len(items),
        f"{prefix}_available_count": sum(item.available for item in items),
        f"{prefix}_resolved_count": sum(item.resolved for item in items),
        f"{prefix}_verified_count": sum(item.verified for item in items),
        f"{prefix}_missing_count": sum(
            item.state is AttributeCompletenessState.MISSING for item in items
        ),
        f"{prefix}_conflicted_count": sum(
            item.state is AttributeCompletenessState.CONFLICTED for item in items
        ),
        f"{prefix}_indeterminate_count": sum(
            item.state is AttributeCompletenessState.INDETERMINATE for item in items
        ),
        f"{prefix}_invalid_count": sum(
            item.state is AttributeCompletenessState.INVALID_ONLY for item in items
        ),
    }


def completeness_status(
    required: tuple[AttributeCompletenessAssessment, ...],
    all_attributes: tuple[AttributeCompletenessAssessment, ...],
) -> AttributeCompletenessStatus:
    if not any(item.available for item in all_attributes):
        return AttributeCompletenessStatus.NO_USABLE_ATTRIBUTES
    states = {item.state for item in required}
    if AttributeCompletenessState.CONFLICTED in states:
        return AttributeCompletenessStatus.CONFLICTED
    if states & {AttributeCompletenessState.MISSING, AttributeCompletenessState.INVALID_ONLY}:
        return AttributeCompletenessStatus.INCOMPLETE
    if AttributeCompletenessState.INDETERMINATE in states:
        return AttributeCompletenessStatus.INDETERMINATE
    if AttributeCompletenessState.PRESENT_SINGLE_SOURCE in states:
        return AttributeCompletenessStatus.COMPLETE_WITH_SINGLE_SOURCE
    return AttributeCompletenessStatus.COMPLETE
