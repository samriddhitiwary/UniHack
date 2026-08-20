"""Deterministic grounding and hallucination rejection tests."""

from dataclasses import replace

import pytest

from app.domain.catalog_enrichment import (
    ClaimRiskCode,
    EnrichmentWarningCode,
    TrustedCatalogFact,
)
from app.services.catalog_enrichment_grounding_validator import (
    CatalogEnrichmentGroundingValidator,
)
from app.services.catalog_enrichment_hallucination_guard import (
    CatalogEnrichmentHallucinationGuard,
)
from tests.fixtures.catalog_enrichment import enrichment_projection, grounded_payload, trusted_facts
from tests.unit.test_catalog_enrichment_prompt_and_parser import parser


def validate(payload, facts):
    content = parser().parse(__import__("json").dumps(payload))
    return CatalogEnrichmentGroundingValidator(CatalogEnrichmentHallucinationGuard()).validate(
        content, facts
    )


def test_grounded_content_has_full_validation_score_inputs() -> None:
    _, _, projection = enrichment_projection()
    result = validate(grounded_payload(projection), trusted_facts(projection))
    assert result.valid
    assert result.grounded_fact_count == result.referenced_fact_count


def test_unknown_fact_reference_is_rejected() -> None:
    _, _, projection = enrichment_projection()
    payload = grounded_payload(projection)
    payload["title"]["factIds"] = ["ATTRIBUTE:efficiency"]
    result = validate(payload, trusted_facts(projection))
    assert ClaimRiskCode.UNKNOWN_FACT_REFERENCE in result.issue_codes


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("95% efficiency", ClaimRiskCode.UNSUPPORTED_NUMERIC_CLAIM),
        ("7.5 hp", ClaimRiskCode.UNSUPPORTED_NUMERIC_CLAIM),
        ("IE3 certified", ClaimRiskCode.UNSUPPORTED_CERTIFICATION_CLAIM),
        ("CE compliant", ClaimRiskCode.UNSUPPORTED_CERTIFICATION_CLAIM),
        ("10 year warranty", ClaimRiskCode.UNSUPPORTED_WARRANTY_CLAIM),
        ("stainless steel", ClaimRiskCode.UNSUPPORTED_MATERIAL_CLAIM),
        ("high efficiency", ClaimRiskCode.UNSUPPORTED_PERFORMANCE_CLAIM),
        ("for chemical plants", ClaimRiskCode.UNSUPPORTED_USE_CASE_CLAIM),
    ],
)
def test_unsupported_high_risk_claims_are_rejected(text: str, code: ClaimRiskCode) -> None:
    _, _, projection = enrichment_projection()
    payload = grounded_payload(projection)
    payload["title"] = {"text": text, "factIds": [projection.attributes[0].attribute_name]}
    payload["title"]["factIds"] = [f"ATTRIBUTE:{projection.attributes[0].attribute_name}"]
    result = validate(payload, trusted_facts(projection))
    assert not result.valid
    assert code in result.issue_codes or (
        code is ClaimRiskCode.UNSUPPORTED_WARRANTY_CLAIM
        and ClaimRiskCode.UNSUPPORTED_NUMERIC_CLAIM in result.issue_codes
    )


def test_supported_reviewed_material_claim_is_allowed() -> None:
    _, _, projection = enrichment_projection()
    facts = trusted_facts(projection)
    material = TrustedCatalogFact(
        fact_id="ATTRIBUTE:material",
        display_name="Material",
        value="stainless steel",
        origin="HUMAN_OVERRIDE",
    )
    facts = replace(facts, facts=(*facts.facts, material))
    payload = grounded_payload(projection)
    payload["title"] = {"text": "stainless steel", "factIds": [material.fact_id]}
    assert validate(payload, facts).valid


@pytest.mark.parametrize(
    ("projection_kwargs", "warning"),
    [
        ({"manual": True}, EnrichmentWarningCode.HUMAN_OVERRIDE_PRESENT),
        ({"warning": True}, EnrichmentWarningCode.VALIDATION_WARNING_PRESENT),
    ],
)
def test_review_origin_and_validation_warning_are_preserved(projection_kwargs, warning) -> None:
    _, _, projection = enrichment_projection(**projection_kwargs)
    result = validate(grounded_payload(projection), trusted_facts(projection))
    assert result.valid
    assert warning in result.warning_codes
