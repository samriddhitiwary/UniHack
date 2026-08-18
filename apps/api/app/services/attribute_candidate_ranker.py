"""Stable ranking for equivalent eligible normalized candidates."""

from app.domain.attribute_normalization import NormalizedAttributeCandidate
from app.domain.attribute_validation import CandidateValidationAssessment, CandidateValidationStatus


class AttributeCandidateRanker:
    def rank(
        self,
        candidates: tuple[NormalizedAttributeCandidate, ...],
        assessments: dict[str, CandidateValidationAssessment],
    ) -> tuple[NormalizedAttributeCandidate, ...]:
        return tuple(
            sorted(
                candidates,
                key=lambda value: (
                    -_validation_rank(assessments[value.normalized_candidate_id].status),
                    -value.extraction_confidence_bp,
                    -value.normalization_confidence_bp,
                    value.normalized_candidate_id,
                ),
            )
        )


def _validation_rank(status: CandidateValidationStatus) -> int:
    return {
        CandidateValidationStatus.VALID: 4,
        CandidateValidationStatus.VALID_WITH_WARNINGS: 3,
        CandidateValidationStatus.INVALID: 2,
        CandidateValidationStatus.NOT_VALIDATABLE: 1,
    }[status]
