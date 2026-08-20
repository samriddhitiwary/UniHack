"""Explicitly opt-in live provider connectivity contract."""

import os

import pytest

from app.core.config import get_settings
from app.services.catalog_enrichment_llm import OpenAICatalogEnrichmentLlm

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_AI_ENRICHMENT_TEST") != "1",
    reason="set RUN_LIVE_AI_ENRICHMENT_TEST=1 with provider credentials to opt in",
)


def test_configured_provider_returns_machine_readable_content() -> None:
    provider = OpenAICatalogEnrichmentLlm(get_settings())
    response = provider.generate(
        system_prompt="Return only strict JSON. Do not use tools.",
        user_prompt='Return exactly {"ok":true}.',
    )
    assert response.strip().startswith("{") and response.strip().endswith("}")
