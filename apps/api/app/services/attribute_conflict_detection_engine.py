"""Deterministic grouping and agreement/conflict assessment."""

from collections import OrderedDict
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from app.core.exceptions import (
    AttributeConflictAttributeLimitExceededError,
    AttributeConflictCandidateLimitExceededError,
    AttributeConflictDetectionError,
    AttributeConflictGroupLimitExceededError,
)
from app.domain.attribute_conflicts import (
    AttributeConflictDetectionResult,
    AttributeConflictType,
    AttributeConsensus,
    AttributeConsensusStatus,
    CandidateAgreementGroup,
)
from app.domain.attribute_normalization import (
    AttributeNormalizationResult,
    NormalizationStatus,
    NormalizedAttributeCandidate,
)
from app.domain.category_schemas import AttributeDataType
from app.services.attribute_numeric_comparator import AttributeNumericComparator
from app.services.attribute_text_comparator import text_comparison_form

_DIRECT = {
    NormalizationStatus.NORMALIZED,
    NormalizationStatus.NORMALIZED_WITH_CONVERSION,
    NormalizationStatus.RAW_TEXT_PRESERVED,
}


class AttributeConflictDetectionEngine:
    def __init__(
        self,
        *,
        relative_tolerance_bp: int = 50,
        absolute_tolerance: str = "0.000001",
        max_attributes: int = 100,
        max_candidates_per_attribute: int = 100,
        max_groups_per_attribute: int = 100,
    ) -> None:
        if min(max_attributes, max_candidates_per_attribute, max_groups_per_attribute) < 1:
            raise ValueError("conflict detection limits must be positive")
        self._numeric = AttributeNumericComparator(
            relative_tolerance_bp=relative_tolerance_bp,
            absolute_tolerance=absolute_tolerance,
        )
        self._max_attributes = max_attributes
        self._max_candidates = max_candidates_per_attribute
        self._max_groups = max_groups_per_attribute

    def detect(
        self,
        *,
        job_id: UUID,
        normalization_result: AttributeNormalizationResult,
        now: datetime | None = None,
    ) -> AttributeConflictDetectionResult:
        grouped: OrderedDict[str, list[NormalizedAttributeCandidate]] = OrderedDict()
        for candidate in normalization_result.candidates:
            grouped.setdefault(candidate.attribute_name, []).append(candidate)
        if len(grouped) > self._max_attributes:
            raise AttributeConflictAttributeLimitExceededError()
        attributes = tuple(self._assess(name, candidates) for name, candidates in grouped.items())
        return AttributeConflictDetectionResult.create(
            job_id=job_id,
            product_id=normalization_result.product_id,
            normalization_id=normalization_result.normalization_id,
            extraction_id=normalization_result.extraction_id,
            classification_id=normalization_result.classification_id,
            category=normalization_result.category,
            schema_version=normalization_result.schema_version,
            schema_fingerprint=normalization_result.schema_fingerprint,
            attributes=attributes,
            now=now or datetime.now(UTC),
        )

    def _assess(
        self, name: str, candidates: list[NormalizedAttributeCandidate]
    ) -> AttributeConsensus:
        if len(candidates) > self._max_candidates:
            raise AttributeConflictCandidateLimitExceededError()
        first = candidates[0]
        excluded = [
            item
            for item in candidates
            if item.normalization_status
            in {NormalizationStatus.UNSUPPORTED_UNIT, NormalizationStatus.INVALID_VALUE}
        ]
        direct = [item for item in candidates if item.normalization_status in _DIRECT]
        missing = [
            item
            for item in candidates
            if item.normalization_status is NormalizationStatus.UNIT_MISSING
        ]
        warnings: list[str] = []
        conflict_type = None
        if excluded:
            warnings.append(AttributeConflictType.MIXED_VALIDITY.value)
        if missing and direct:
            comparable = direct + missing
            status = AttributeConsensusStatus.INDETERMINATE
            confidence = 5_000
            conflict_type = AttributeConflictType.UNIT_INDETERMINATE
            warnings.append(conflict_type.value)
        else:
            comparable = direct or missing
            status, confidence, conflict_type = self._compare(first.data_type, comparable)
        groups = self._groups(comparable)
        if len(groups) > self._max_groups:
            raise AttributeConflictGroupLimitExceededError()
        return AttributeConsensus(
            attribute_name=name,
            attribute_display_name=first.attribute_display_name,
            data_type=first.data_type,
            status=status,
            candidate_count=len(candidates),
            comparable_candidate_count=len(comparable),
            excluded_candidate_count=len(excluded),
            distinct_source_count=len({item.source_id for item in candidates}),
            agreement_group_count=len(groups),
            conflict_type=conflict_type,
            candidate_ids=tuple(item.normalized_candidate_id for item in candidates),
            groups=groups,
            consensus_confidence_bp=confidence,
            warning_codes=tuple(warnings),
        )

    def _compare(
        self, data_type: AttributeDataType, candidates: list[NormalizedAttributeCandidate]
    ) -> tuple[AttributeConsensusStatus, int, AttributeConflictType | None]:
        if not candidates:
            return AttributeConsensusStatus.NO_VALID_CANDIDATES, 10_000, None
        if len(candidates) == 1:
            return AttributeConsensusStatus.SINGLE_CANDIDATE, 6_000, None
        source_count = len({item.source_id for item in candidates})
        values = [item.normalized_value for item in candidates]
        if any(value is None for value in values):
            return (
                AttributeConsensusStatus.INDETERMINATE,
                5_000,
                AttributeConflictType.UNIT_INDETERMINATE,
            )
        if data_type in {AttributeDataType.NUMBER, AttributeDataType.INTEGER}:
            units = {item.normalized_unit for item in candidates}
            if len(units) != 1:
                return (
                    AttributeConsensusStatus.INDETERMINATE,
                    5_000,
                    AttributeConflictType.UNIT_INDETERMINATE,
                )
            decimals = [self._numeric.parse(value or "") for value in values]
            if any(value is None for value in decimals):
                raise AttributeConflictDetectionError()
            parsed = cast(list[Decimal], decimals)
            comparisons = [
                self._numeric.compare(
                    parsed[left], parsed[right], integer=data_type is AttributeDataType.INTEGER
                )
                for left in range(len(parsed))
                for right in range(left + 1, len(parsed))
            ]
            if all(item == "EXACT" for item in comparisons):
                return (
                    AttributeConsensusStatus.AGREEMENT,
                    10_000 if source_count >= 2 else 8_500,
                    None,
                )
            if all(item in {"EXACT", "TOLERANCE"} for item in comparisons):
                return (
                    AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE,
                    9_000 if source_count >= 2 else 8_000,
                    None,
                )
            return AttributeConsensusStatus.CONFLICT, 10_000, AttributeConflictType.VALUE_CONFLICT
        forms = [text_comparison_form(value or "") for value in values]
        if len(set(forms)) == 1:
            return AttributeConsensusStatus.AGREEMENT, 10_000 if source_count >= 2 else 8_500, None
        return AttributeConsensusStatus.CONFLICT, 10_000, AttributeConflictType.VALUE_CONFLICT

    @staticmethod
    def _groups(
        candidates: list[NormalizedAttributeCandidate],
    ) -> tuple[CandidateAgreementGroup, ...]:
        grouped: OrderedDict[tuple[str, str | None], list[NormalizedAttributeCandidate]] = (
            OrderedDict()
        )
        for item in candidates:
            if item.normalized_value is None:
                continue
            key = (item.normalized_value, item.normalized_unit)
            grouped.setdefault(key, []).append(item)
        return tuple(
            CandidateAgreementGroup(
                group_id=f"group-{index:06d}",
                normalized_value=key[0],
                normalized_unit=key[1],
                candidate_ids=tuple(item.normalized_candidate_id for item in values),
                distinct_source_ids=tuple(dict.fromkeys(item.source_id for item in values)),
                candidate_count=len(values),
                distinct_source_count=len({item.source_id for item in values}),
            )
            for index, (key, values) in enumerate(grouped.items(), 1)
        )
