"""Provider-independent grounded catalog enrichment engine."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    CatalogEnrichmentGroundingFailedError,
    CatalogEnrichmentOutputLimitError,
    CatalogEnrichmentResponseInvalidError,
)
from app.domain.catalog_enrichment import (
    CatalogEnrichmentResult,
    ClaimRiskCode,
    TrustedCatalogFacts,
)
from app.domain.catalog_projection import CommerceCatalogProjection
from app.services.catalog_enrichment_grounding_validator import (
    CatalogEnrichmentGroundingValidator,
)
from app.services.catalog_enrichment_llm import CatalogEnrichmentLlm
from app.services.catalog_enrichment_prompt_builder import (
    CatalogEnrichmentPrompt,
    CatalogEnrichmentPromptBuilder,
)
from app.services.catalog_enrichment_response_parser import CatalogEnrichmentResponseParser
from app.services.catalog_enrichment_trusted_facts import CatalogEnrichmentTrustedFactBuilder


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogEnrichmentPreparation:
    facts: TrustedCatalogFacts
    prompt: CatalogEnrichmentPrompt


class CatalogEnrichmentEngine:
    def __init__(
        self,
        *,
        llm: CatalogEnrichmentLlm,
        fact_builder: CatalogEnrichmentTrustedFactBuilder,
        prompt_builder: CatalogEnrichmentPromptBuilder,
        parser: CatalogEnrichmentResponseParser,
        validator: CatalogEnrichmentGroundingValidator,
        max_attempts: int,
    ) -> None:
        self._llm = llm
        self._facts = fact_builder
        self._prompts = prompt_builder
        self._parser = parser
        self._validator = validator
        self._max_attempts = max_attempts

    @property
    def provider(self) -> str:
        return self._llm.provider

    @property
    def model(self) -> str:
        return self._llm.model

    def prepare(self, projection: CommerceCatalogProjection) -> CatalogEnrichmentPreparation:
        facts = self._facts.build(projection)
        return CatalogEnrichmentPreparation(facts=facts, prompt=self._prompts.build(facts))

    def generate(
        self,
        *,
        preparation: CatalogEnrichmentPreparation,
        projection: CommerceCatalogProjection,
        job_id: UUID,
        enrichment_id: UUID,
        created_at: datetime,
    ) -> CatalogEnrichmentResult:
        prompt = preparation.prompt
        final_invalid: (
            CatalogEnrichmentResponseInvalidError | CatalogEnrichmentOutputLimitError | None
        ) = None
        for attempt in range(1, self._max_attempts + 1):
            raw = self._llm.generate(
                system_prompt=prompt.system_prompt,
                user_prompt=prompt.user_prompt,
            )
            try:
                content = self._parser.parse(raw)
            except (
                CatalogEnrichmentResponseInvalidError,
                CatalogEnrichmentOutputLimitError,
            ) as exc:
                final_invalid = exc
                if attempt == self._max_attempts:
                    raise
                prompt = self._prompts.build(
                    preparation.facts,
                    correction_issue_codes=(ClaimRiskCode.UNGROUNDED_CONTENT,),
                )
                continue
            validation = self._validator.validate(content, preparation.facts)
            if not validation.valid:
                if attempt == self._max_attempts:
                    raise CatalogEnrichmentGroundingFailedError()
                prompt = self._prompts.build(
                    preparation.facts,
                    correction_issue_codes=validation.issue_codes,
                )
                continue
            referenced = {fact_id for item in content.all_items() for fact_id in item.fact_ids}
            fact_count = len(preparation.facts.facts)
            return CatalogEnrichmentResult(
                enrichment_id=enrichment_id,
                job_id=job_id,
                product_id=projection.product_id,
                projection_id=projection.projection_id,
                projection_product_version=projection.product_version,
                category=projection.category,
                schema_version=projection.schema_version,
                schema_fingerprint=projection.schema_fingerprint,
                title=content.title,
                description=content.description,
                feature_bullets=content.feature_bullets,
                search_keywords=content.search_keywords,
                technical_summary=content.technical_summary,
                trusted_fact_count=fact_count,
                referenced_fact_count=len(referenced),
                fact_coverage_bp=len(referenced) * 10_000 // fact_count,
                grounding_score_bp=10_000,
                warning_codes=validation.warning_codes,
                provider=self.provider,
                model=self.model,
                prompt_version=prompt.prompt_version,
                prompt_sha256=prompt.prompt_sha256,
                generation_attempt_count=attempt,
                engine="grounded-commerce-content-generator-v1",
                engine_version="1.0",
                created_at=created_at,
            )
        if final_invalid:
            raise final_invalid
        raise CatalogEnrichmentGroundingFailedError()
