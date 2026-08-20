"""Provider-independent catalog enrichment LLM boundary and OpenAI adapter."""

from typing import Protocol

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from app.core.config import Settings
from app.core.exceptions import (
    CatalogEnrichmentProviderFailedError,
    CatalogEnrichmentProviderRateLimitedError,
    CatalogEnrichmentProviderTimeoutError,
    CatalogEnrichmentProviderUnavailableError,
)


class CatalogEnrichmentLlm(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model(self) -> str: ...

    def generate(self, *, system_prompt: str, user_prompt: str) -> str: ...


class OpenAICatalogEnrichmentLlm:
    """OpenAI Responses API adapter with no tools and bounded output."""

    def __init__(self, settings: Settings) -> None:
        secret = settings.ai_enrichment_api_key
        key = secret.get_secret_value().strip() if secret else ""
        if not key or not settings.ai_enrichment_model:
            raise CatalogEnrichmentProviderUnavailableError()
        self._model = settings.ai_enrichment_model
        self._temperature = settings.ai_enrichment_temperature
        self._max_tokens = settings.ai_enrichment_max_output_tokens
        self._client = OpenAI(api_key=key, timeout=settings.ai_enrichment_timeout_seconds)

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def generate(self, *, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.responses.create(
                model=self._model,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=self._max_tokens,
                temperature=self._temperature,
                tools=[],
            )
            if not response.output_text:
                raise CatalogEnrichmentProviderFailedError()
            return response.output_text
        except APITimeoutError as exc:
            raise CatalogEnrichmentProviderTimeoutError() from exc
        except RateLimitError as exc:
            raise CatalogEnrichmentProviderRateLimitedError() from exc
        except APIConnectionError as exc:
            raise CatalogEnrichmentProviderUnavailableError() from exc
        except CatalogEnrichmentProviderFailedError:
            raise
        except Exception as exc:
            raise CatalogEnrichmentProviderFailedError() from exc
