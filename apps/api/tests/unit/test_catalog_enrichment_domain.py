"""Catalog enrichment immutable result invariant tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from tests.fixtures.catalog_enrichment import FakeLlm, enrichment_projection, grounded_response
from tests.unit.test_catalog_enrichment_engine import engine, generate


def result_fixture():
    _, _, projection = enrichment_projection()
    return generate(engine(FakeLlm([grounded_response(projection)])), projection)


def test_result_and_content_are_immutable_and_coherent() -> None:
    result = result_fixture()
    with pytest.raises(FrozenInstanceError):
        result.provider = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.title.text = "changed"  # type: ignore[misc]
    expected = result.referenced_fact_count * 10_000 // result.trusted_fact_count
    assert result.fact_coverage_bp == expected


@pytest.mark.parametrize(
    "changes",
    [
        {"generation_attempt_count": 0},
        {"grounding_score_bp": 9_999},
        {"prompt_sha256": "bad"},
        {"feature_bullets": ()},
        {"search_keywords": ()},
    ],
)
def test_result_rejects_invalid_counts_hashes_or_scores(changes) -> None:
    with pytest.raises(ValueError):
        replace(result_fixture(), **changes)
