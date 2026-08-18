from dataclasses import replace

from app.services.attribute_candidate_ranker import AttributeCandidateRanker
from tests.unit.test_attribute_selection_engine import pipeline


def test_ranking_is_confidence_driven_stable_and_input_order_independent() -> None:
    _, normalization, _, validation, _, _ = pipeline(
        ("voltage", "415", "V"), ("voltage", "415", "V")
    )
    first, second = normalization.candidates
    first = replace(first, extraction_confidence_bp=8_000, normalization_confidence_bp=8_000)
    second = replace(second, extraction_confidence_bp=9_000, normalization_confidence_bp=9_000)
    assessments = {item.normalized_candidate_id: item for item in validation.assessments}
    ranker = AttributeCandidateRanker()
    assert (
        ranker.rank((first, second), assessments)[0].normalized_candidate_id
        == second.normalized_candidate_id
    )
    assert ranker.rank((second, first), assessments) == ranker.rank((first, second), assessments)
