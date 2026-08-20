"""Trusted projection fact construction tests."""

from dataclasses import replace

import pytest

from app.core.exceptions import CatalogEnrichmentTrustedFactLimitError
from app.services.catalog_enrichment_trusted_facts import CatalogEnrichmentTrustedFactBuilder
from tests.fixtures.catalog_enrichment import enrichment_projection


def test_stable_identity_attribute_facts_preserve_review_metadata_without_evidence() -> None:
    _, _, projection = enrichment_projection()
    facts = CatalogEnrichmentTrustedFactBuilder(max_facts=200, max_value_characters=10_000).build(
        projection
    )
    identifiers = [fact.fact_id for fact in facts.facts]
    assert identifiers[:2] == ["IDENTITY:name", "IDENTITY:category"]
    assert "IDENTITY:manufacturer" in identifiers
    assert all(not hasattr(fact, "source_id") for fact in facts.facts)
    attribute = next(fact for fact in facts.facts if fact.fact_id.startswith("ATTRIBUTE:"))
    assert attribute.origin is not None


def test_missing_optional_identity_is_omitted_and_limits_are_controlled() -> None:
    _, _, projection = enrichment_projection(manufacturer=None, model_number=None, description=None)
    builder = CatalogEnrichmentTrustedFactBuilder(max_facts=200, max_value_characters=10_000)
    facts = builder.build(projection)
    assert not any(fact.fact_id == "IDENTITY:manufacturer" for fact in facts.facts)
    with pytest.raises(CatalogEnrichmentTrustedFactLimitError):
        CatalogEnrichmentTrustedFactBuilder(max_facts=1, max_value_characters=10_000).build(
            projection
        )
    with pytest.raises(CatalogEnrichmentTrustedFactLimitError):
        builder = CatalogEnrichmentTrustedFactBuilder(max_facts=200, max_value_characters=2)
        builder.build(replace(projection, product_name="long"))
