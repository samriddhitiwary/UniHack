"""Deterministic schema-driven attribute completeness evaluation."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    AttributeCompletenessAttributeLimitExceededError,
    AttributeCompletenessCandidateIdLimitExceededError,
    AttributeCompletenessSchemaMismatchError,
)
from app.domain.attribute_completeness import (
    AttributeCompletenessAssessment,
    AttributeCompletenessResult,
    AttributeCompletenessState,
    state_flags,
)
from app.domain.attribute_conflicts import (
    AttributeConflictDetectionResult,
    AttributeConsensus,
    AttributeConsensusStatus,
)
from app.domain.category_schemas import AttributeDefinition, CategoryAttributeSchema

logger = logging.getLogger(__name__)

_STATE_BY_CONSENSUS = {
    AttributeConsensusStatus.AGREEMENT: AttributeCompletenessState.PRESENT,
    AttributeConsensusStatus.AGREEMENT_WITH_TOLERANCE: (
        AttributeCompletenessState.PRESENT_WITH_TOLERANCE
    ),
    AttributeConsensusStatus.SINGLE_CANDIDATE: (AttributeCompletenessState.PRESENT_SINGLE_SOURCE),
    AttributeConsensusStatus.CONFLICT: AttributeCompletenessState.CONFLICTED,
    AttributeConsensusStatus.INDETERMINATE: AttributeCompletenessState.INDETERMINATE,
    AttributeConsensusStatus.NO_VALID_CANDIDATES: AttributeCompletenessState.INVALID_ONLY,
}


class AttributeCompletenessEngine:
    def __init__(
        self, *, max_attributes: int = 100, max_candidate_ids_per_attribute: int = 100
    ) -> None:
        if max_attributes < 1 or max_candidate_ids_per_attribute < 1:
            raise ValueError("completeness limits must be positive")
        self._max_attributes = max_attributes
        self._max_candidate_ids = max_candidate_ids_per_attribute

    def evaluate(
        self,
        *,
        job_id: UUID,
        conflict_result: AttributeConflictDetectionResult,
        schema: CategoryAttributeSchema,
        now: datetime | None = None,
    ) -> AttributeCompletenessResult:
        if (
            schema.category != conflict_result.category
            or schema.version != conflict_result.schema_version
            or schema.schema_fingerprint != conflict_result.schema_fingerprint
        ):
            raise AttributeCompletenessSchemaMismatchError()
        if len(schema.attributes) > self._max_attributes:
            raise AttributeCompletenessAttributeLimitExceededError()
        consensus_by_name = {item.attribute_name: item for item in conflict_result.attributes}
        attributes = tuple(
            self._assess(definition, consensus_by_name.get(definition.canonical_name))
            for definition in sorted(schema.attributes, key=lambda item: item.display_order)
        )
        return AttributeCompletenessResult.create(
            job_id=job_id,
            product_id=conflict_result.product_id,
            conflict_detection_id=conflict_result.conflict_detection_id,
            normalization_id=conflict_result.normalization_id,
            extraction_id=conflict_result.extraction_id,
            classification_id=conflict_result.classification_id,
            category=conflict_result.category,
            schema_version=conflict_result.schema_version,
            schema_fingerprint=conflict_result.schema_fingerprint,
            attributes=attributes,
            now=now or datetime.now(UTC),
        )

    def _assess(
        self, definition: AttributeDefinition, consensus: AttributeConsensus | None
    ) -> AttributeCompletenessAssessment:
        if consensus is None:
            state = AttributeCompletenessState.MISSING
            candidate_count = comparable_count = source_count = 0
            consensus_status = confidence = conflict_type = None
            candidate_ids: tuple[str, ...] = ()
            warnings: tuple[str, ...] = (
                ("MISSING_REQUIRED",) if definition.required else ("MISSING_OPTIONAL",)
            )
        else:
            if len(consensus.candidate_ids) > self._max_candidate_ids:
                raise AttributeCompletenessCandidateIdLimitExceededError()
            state = _STATE_BY_CONSENSUS[consensus.status]
            candidate_count = consensus.candidate_count
            comparable_count = consensus.comparable_candidate_count
            source_count = consensus.distinct_source_count
            consensus_status = consensus.status
            confidence = consensus.consensus_confidence_bp
            conflict_type = consensus.conflict_type
            candidate_ids = consensus.candidate_ids
            warnings = consensus.warning_codes
        available, resolved, verified = state_flags(state)
        assessment = AttributeCompletenessAssessment(
            attribute_name=definition.canonical_name,
            attribute_display_name=definition.display_name,
            required=definition.required,
            display_order=definition.display_order,
            state=state,
            candidate_count=candidate_count,
            comparable_candidate_count=comparable_count,
            distinct_source_count=source_count,
            consensus_status=consensus_status,
            consensus_confidence_bp=confidence,
            conflict_type=conflict_type,
            available=available,
            resolved=resolved,
            verified=verified,
            candidate_ids=candidate_ids,
            warning_codes=warnings,
        )
        logger.info(
            "event=attribute_completeness.attribute_evaluated attribute_name=%s required=%s "
            "state=%s candidate_count=%s distinct_source_count=%s",
            assessment.attribute_name,
            assessment.required,
            assessment.state.value,
            assessment.candidate_count,
            assessment.distinct_source_count,
        )
        return assessment
