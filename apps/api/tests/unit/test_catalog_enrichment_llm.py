"""Configured provider adapter safety tests."""

import pytest
from httpx import Request, Response
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.core.config import Settings
from app.core.exceptions import (
    CatalogEnrichmentProviderFailedError,
    CatalogEnrichmentProviderRateLimitedError,
    CatalogEnrichmentProviderTimeoutError,
    CatalogEnrichmentProviderUnavailableError,
)
from app.services.catalog_enrichment_llm import OpenAICatalogEnrichmentLlm


def test_openai_adapter_requires_configured_secret_and_model() -> None:
    with pytest.raises(CatalogEnrichmentProviderUnavailableError):
        OpenAICatalogEnrichmentLlm(Settings(ai_enrichment_api_key=None, ai_enrichment_model=""))


def test_provider_secret_uses_masked_configuration_type() -> None:
    settings = Settings(ai_enrichment_api_key="secret-value", ai_enrichment_model="test-model")
    assert "secret-value" not in repr(settings.ai_enrichment_api_key)


class Responses:
    def __init__(self, outcome) -> None:
        self.outcome = outcome

    def create(self, **kwargs):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return type("ProviderResponse", (), {"output_text": self.outcome})()


class Client:
    def __init__(self, outcome) -> None:
        self.responses = Responses(outcome)


def adapter(outcome):
    subject = OpenAICatalogEnrichmentLlm(
        Settings(ai_enrichment_api_key="secret", ai_enrichment_model="test-model")
    )
    subject._client = Client(outcome)  # type: ignore[assignment]
    return subject


def test_adapter_returns_text_without_exposing_provider_details() -> None:
    subject = adapter('{"ok":true}')
    assert subject.provider == "openai" and subject.model == "test-model"
    assert subject.generate(system_prompt="safe", user_prompt="data") == '{"ok":true}'


@pytest.mark.parametrize(
    ("provider_error", "controlled"),
    [
        (
            APITimeoutError(request=Request("POST", "https://api.openai.com/v1/responses")),
            CatalogEnrichmentProviderTimeoutError,
        ),
        (
            APIConnectionError(request=Request("POST", "https://api.openai.com/v1/responses")),
            CatalogEnrichmentProviderUnavailableError,
        ),
        (
            RateLimitError(
                "limited",
                response=Response(
                    429, request=Request("POST", "https://api.openai.com/v1/responses")
                ),
                body=None,
            ),
            CatalogEnrichmentProviderRateLimitedError,
        ),
        (RuntimeError("provider internals"), CatalogEnrichmentProviderFailedError),
    ],
)
def test_provider_failures_map_to_safe_controlled_errors(provider_error, controlled) -> None:
    with pytest.raises(controlled):
        adapter(provider_error).generate(system_prompt="safe", user_prompt="data")
