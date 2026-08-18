"""Conservative deterministic proposed-selection and review preparation."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeSelectionAttributeLimitExceededError,
    AttributeSelectionCandidateLimitExceededError,
    AttributeSelectionLineageMismatchError,
    AttributeSelectionReasonLimitExceededError,
)
from app.domain.attribute_completeness import (
    AttributeCompletenessAssessment,
    AttributeCompletenessResult,
    AttributeCompletenessState,
)
from app.domain.attribute_conflicts import (
    AttributeConflictDetectionResult,
    AttributeConsensus,
    AttributeConsensusStatus,
)
from app.domain.attribute_normalization import (
    AttributeNormalizationResult,
    NormalizedAttributeCandidate,
)
from app.domain.attribute_selection import (
    AttributeSelectionResult,
    AttributeSelectionStatus,
    ProposedAttributeSelection,
    SelectionReasonCode,
)
from app.domain.attribute_validation import (
    AttributeValidationResult,
    CandidateValidationAssessment,
    CandidateValidationStatus,
)
from app.services.attribute_candidate_ranker import AttributeCandidateRanker

logger = logging.getLogger(__name__)


class AttributeSelectionEngine:
    def __init__(
        self,
        *,
        auto_select_min_confidence_bp: int = 9_000,
        min_distinct_sources: int = 2,
        max_attributes: int = 100,
        max_candidate_ids_per_attribute: int = 100,
        max_reason_codes_per_attribute: int = 20,
    ) -> None:
        if (
            not 0 <= auto_select_min_confidence_bp <= 10_000
            or min(
                min_distinct_sources,
                max_attributes,
                max_candidate_ids_per_attribute,
                max_reason_codes_per_attribute,
            )
            < 1
        ):
            raise ValueError("attribute selection configuration is invalid")
        self._threshold, self._min_sources = auto_select_min_confidence_bp, min_distinct_sources
        self._max_attributes, self._max_ids = max_attributes, max_candidate_ids_per_attribute
        self._max_reasons = max_reason_codes_per_attribute
        self._ranker = AttributeCandidateRanker()

    def select(
        self,
        *,
        job_id: UUID,
        conflict_result: AttributeConflictDetectionResult,
        validation_result: AttributeValidationResult,
        completeness_result: AttributeCompletenessResult,
        normalization_result: AttributeNormalizationResult,
        now: datetime | None = None,
    ) -> AttributeSelectionResult:
        self._validate_lineage(
            conflict_result, validation_result, completeness_result, normalization_result
        )
        if len(completeness_result.attributes) > self._max_attributes:
            raise AttributeSelectionAttributeLimitExceededError()
        candidates = {
            item.normalized_candidate_id: item for item in normalization_result.candidates
        }
        validations = {item.normalized_candidate_id: item for item in validation_result.assessments}
        if set(candidates) != set(validations):
            raise AttributeSelectionLineageMismatchError()
        consensus = {item.attribute_name: item for item in conflict_result.attributes}
        output = tuple(
            self._select_attribute(
                item, consensus.get(item.attribute_name), candidates, validations
            )
            for item in completeness_result.attributes
        )
        return AttributeSelectionResult.create(
            job_id=job_id,
            product_id=conflict_result.product_id,
            conflict_detection_id=conflict_result.conflict_detection_id,
            validation_id=validation_result.validation_id,
            completeness_id=completeness_result.completeness_id,
            normalization_id=normalization_result.normalization_id,
            extraction_id=normalization_result.extraction_id,
            classification_id=normalization_result.classification_id,
            category=normalization_result.category,
            schema_version=normalization_result.schema_version,
            schema_fingerprint=normalization_result.schema_fingerprint,
            attributes=output,
            now=(now or datetime.now(UTC)).astimezone(UTC),
        )

    @staticmethod
    def _validate_lineage(
        conflict: AttributeConflictDetectionResult,
        validation: AttributeValidationResult,
        completeness: AttributeCompletenessResult,
        normalization: AttributeNormalizationResult,
    ) -> None:
        product_ids = {
            conflict.product_id,
            validation.product_id,
            completeness.product_id,
            normalization.product_id,
        }
        lineage = {
            (
                value.normalization_id,
                value.extraction_id,
                value.classification_id,
                value.category,
                value.schema_version,
                value.schema_fingerprint,
            )
            for value in (conflict, validation, completeness, normalization)
        }
        if (
            len(product_ids) != 1
            or len(lineage) != 1
            or completeness.conflict_detection_id != conflict.conflict_detection_id
            or validation.normalization_id != normalization.normalization_id
        ):
            raise AttributeSelectionLineageMismatchError()

    def _select_attribute(
        self,
        completeness: AttributeCompletenessAssessment,
        consensus: AttributeConsensus | None,
        candidates: dict[str, NormalizedAttributeCandidate],
        validations: dict[str, CandidateValidationAssessment],
    ) -> ProposedAttributeSelection:
        if completeness.state is AttributeCompletenessState.MISSING:
            return self._build(
                completeness,
                AttributeSelectionStatus.NO_CANDIDATE,
                completeness.required,
                None,
                (),
                (),
                0,
                0,
                0,
                None,
                (
                    SelectionReasonCode.MISSING_ATTRIBUTE
                    if completeness.required
                    else SelectionReasonCode.OPTIONAL_ATTRIBUTE_UNRESOLVED,
                ),
            )
        if completeness.state is AttributeCompletenessState.INVALID_ONLY:
            ids = completeness.candidate_ids
            if len(ids) > self._max_ids or any(
                candidate_id not in candidates or candidate_id not in validations
                for candidate_id in ids
            ):
                raise AttributeSelectionCandidateLimitExceededError()
            return self._build(
                completeness,
                AttributeSelectionStatus.NO_VALID_CANDIDATE,
                completeness.required,
                consensus,
                (),
                ids,
                len(ids),
                0,
                len({candidates[i].source_id for i in ids}),
                None,
                (SelectionReasonCode.NO_VALID_CANDIDATE,),
            )
        if consensus is None:
            raise AttributeSelectionLineageMismatchError()
        ids = consensus.candidate_ids
        if len(ids) > self._max_ids or any(
            i not in candidates or i not in validations for i in ids
        ):
            raise AttributeSelectionCandidateLimitExceededError()
        all_candidates = tuple(candidates[i] for i in ids)
        eligible = tuple(
            item
            for item in all_candidates
            if validations[item.normalized_candidate_id].status is CandidateValidationStatus.VALID
        )
        valid_count = sum(
            validations[i].status
            in {CandidateValidationStatus.VALID, CandidateValidationStatus.VALID_WITH_WARNINGS}
            for i in ids
        )
        source_count = len({item.source_id for item in all_candidates})
        has_nonvalid = any(
            validations[i].status is not CandidateValidationStatus.VALID for i in ids
        )
        if consensus.status is AttributeConsensusStatus.NO_VALID_CANDIDATES or not eligible:
            return self._build(
                completeness,
                AttributeSelectionStatus.NO_VALID_CANDIDATE,
                completeness.required,
                consensus,
                (),
                ids,
                len(ids),
                valid_count,
                source_count,
                None,
                (SelectionReasonCode.NO_VALID_CANDIDATE,),
            )
        if consensus.status is AttributeConsensusStatus.CONFLICT:
            return self._review(
                completeness,
                consensus,
                ids,
                len(ids),
                valid_count,
                source_count,
                0,
                SelectionReasonCode.VALUE_CONFLICT,
            )
        if consensus.status is AttributeConsensusStatus.INDETERMINATE:
            return self._review(
                completeness,
                consensus,
                ids,
                len(ids),
                valid_count,
                source_count,
                0,
                SelectionReasonCode.UNIT_INDETERMINATE,
            )
        if consensus.status is AttributeConsensusStatus.SINGLE_CANDIDATE:
            return self._review(
                completeness,
                consensus,
                ids,
                len(ids),
                valid_count,
                source_count,
                6_000,
                SelectionReasonCode.SINGLE_SOURCE_ONLY,
            )
        if has_nonvalid:
            return self._review(
                completeness,
                consensus,
                ids,
                len(ids),
                valid_count,
                source_count,
                0,
                SelectionReasonCode.VALIDATION_WARNING,
            )
        confidence = 10_000 if consensus.status is AttributeConsensusStatus.AGREEMENT else 9_000
        if source_count < self._min_sources:
            return self._review(
                completeness,
                consensus,
                ids,
                len(ids),
                valid_count,
                source_count,
                7_000,
                SelectionReasonCode.INSUFFICIENT_CORROBORATION,
            )
        units = {item.normalized_unit for item in eligible}
        values = {item.normalized_value for item in eligible}
        exact = consensus.status is AttributeConsensusStatus.AGREEMENT
        if len(units) != 1 or (exact and len(values) != 1) or confidence < self._threshold:
            return self._review(
                completeness,
                consensus,
                ids,
                len(ids),
                valid_count,
                source_count,
                confidence,
                SelectionReasonCode.INSUFFICIENT_CORROBORATION,
            )
        ranked = self._ranker.rank(eligible, validations)
        reason = (
            SelectionReasonCode.MULTI_SOURCE_EXACT_AGREEMENT
            if exact
            else SelectionReasonCode.MULTI_SOURCE_TOLERANCE_AGREEMENT
        )
        return self._build(
            completeness,
            AttributeSelectionStatus.AUTO_SELECTED,
            False,
            consensus,
            tuple(item.normalized_candidate_id for item in ranked),
            (),
            len(ids),
            valid_count,
            source_count,
            ranked[0],
            (reason,),
            confidence,
        )

    def _review(
        self,
        completeness: AttributeCompletenessAssessment,
        consensus: AttributeConsensus,
        ids: tuple[str, ...],
        count: int,
        valid_count: int,
        source_count: int,
        confidence: int,
        reason: SelectionReasonCode,
    ) -> ProposedAttributeSelection:
        return self._build(
            completeness,
            AttributeSelectionStatus.REVIEW_REQUIRED,
            True,
            consensus,
            (),
            ids,
            count,
            valid_count,
            source_count,
            None,
            (reason,),
            confidence,
        )

    def _build(
        self,
        completeness: AttributeCompletenessAssessment,
        status: AttributeSelectionStatus,
        review_required: bool,
        consensus: AttributeConsensus | None,
        supporting_ids: tuple[str, ...],
        review_ids: tuple[str, ...],
        candidate_count: int,
        valid_count: int,
        source_count: int,
        primary: NormalizedAttributeCandidate | None,
        reasons: tuple[SelectionReasonCode, ...],
        confidence: int = 0,
    ) -> ProposedAttributeSelection:
        if len(reasons) > self._max_reasons:
            raise AttributeSelectionReasonLimitExceededError()
        result = ProposedAttributeSelection(
            attribute_name=completeness.attribute_name,
            attribute_display_name=completeness.attribute_display_name,
            required=completeness.required,
            display_order=completeness.display_order,
            selection_status=status,
            review_required=review_required,
            proposed_value=None if primary is None else primary.normalized_value,
            proposed_unit=None if primary is None else primary.normalized_unit,
            primary_candidate_id=None if primary is None else primary.normalized_candidate_id,
            supporting_candidate_ids=supporting_ids,
            review_candidate_ids=review_ids,
            candidate_count=candidate_count,
            valid_candidate_count=valid_count,
            distinct_source_count=source_count,
            consensus_status=None if consensus is None else consensus.status,
            conflict_type=None if consensus is None else consensus.conflict_type,
            selection_confidence_bp=confidence,
            reason_codes=reasons,
            warning_codes=completeness.warning_codes,
        )
        logger.info(
            "event=attribute_selection.%s attribute_name=%s selection_status=%s "
            "candidate_count=%s distinct_source_count=%s selection_confidence_bp=%s",
            status.value.lower(),
            result.attribute_name,
            status.value,
            candidate_count,
            source_count,
            confidence,
        )
        return result
