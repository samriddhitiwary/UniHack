"""Grounded catalog enrichment engine tests."""

import json

import pytest

from app.core.exceptions import (
    CatalogEnrichmentGroundingFailedError,
    CatalogEnrichmentResponseInvalidError,
)
from app.services.catalog_enrichment_engine import CatalogEnrichmentEngine
from app.services.catalog_enrichment_grounding_validator import (
    CatalogEnrichmentGroundingValidator,
)
from app.services.catalog_enrichment_hallucination_guard import (
    CatalogEnrichmentHallucinationGuard,
)
from app.services.catalog_enrichment_prompt_builder import CatalogEnrichmentPromptBuilder
from app.services.catalog_enrichment_trusted_facts import CatalogEnrichmentTrustedFactBuilder
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_enrichment import (
    ENRICHMENT_ID,
    ENRICHMENT_JOB_ID,
    FakeLlm,
    enrichment_projection,
    grounded_payload,
    grounded_response,
)
from tests.unit.test_catalog_enrichment_prompt_and_parser import parser


def engine(llm: FakeLlm, attempts=2) -> CatalogEnrichmentEngine:
    return CatalogEnrichmentEngine(
        llm=llm,
        fact_builder=CatalogEnrichmentTrustedFactBuilder(
            max_facts=200, max_value_characters=10_000
        ),
        prompt_builder=CatalogEnrichmentPromptBuilder(),
        parser=parser(),
        validator=CatalogEnrichmentGroundingValidator(CatalogEnrichmentHallucinationGuard()),
        max_attempts=attempts,
    )


def generate(subject: CatalogEnrichmentEngine, projection):
    return subject.generate(
        preparation=subject.prepare(projection),
        projection=projection,
        job_id=ENRICHMENT_JOB_ID,
        enrichment_id=ENRICHMENT_ID,
        created_at=NOW,
    )


def test_generates_all_immutable_content_and_quality_metadata() -> None:
    _, _, projection = enrichment_projection()
    llm = FakeLlm([grounded_response(projection)])
    result = generate(engine(llm), projection)
    assert result.title.text == projection.product_name
    assert len(result.feature_bullets) == 3
    assert result.search_keywords and result.technical_summary.text
    assert result.grounding_score_bp == 10_000
    assert result.generation_attempt_count == 1
    assert len(llm.calls) == 1


def test_unsafe_first_attempt_retries_and_persists_only_grounded_second() -> None:
    _, _, projection = enrichment_projection()
    unsafe = grounded_payload(projection)
    unsafe["description"] = {
        "text": "95% efficiency",
        "factIds": [f"ATTRIBUTE:{projection.attributes[0].attribute_name}"],
    }
    llm = FakeLlm([json.dumps(unsafe), grounded_response(projection)])
    result = generate(engine(llm), projection)
    assert result.generation_attempt_count == 2
    assert "Previous output failed" in llm.calls[1][1]


def test_two_unsafe_attempts_fail_without_result() -> None:
    _, _, projection = enrichment_projection()
    unsafe = grounded_payload(projection)
    unsafe["description"] = {
        "text": "IE4 certified",
        "factIds": ["IDENTITY:category"],
    }
    llm = FakeLlm([json.dumps(unsafe), json.dumps(unsafe)])
    with pytest.raises(CatalogEnrichmentGroundingFailedError):
        generate(engine(llm), projection)


def test_malformed_response_retries_then_fails_controlled() -> None:
    _, _, projection = enrichment_projection()
    llm = FakeLlm(["bad", "still bad"])
    with pytest.raises(CatalogEnrichmentResponseInvalidError):
        generate(engine(llm), projection)
