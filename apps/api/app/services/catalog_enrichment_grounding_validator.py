"""Validate provider output against the exact trusted-fact vocabulary."""

from app.domain.catalog_enrichment import (
    ClaimRiskCode,
    EnrichmentValidationResult,
    EnrichmentWarningCode,
    TrustedCatalogFacts,
)
from app.services.catalog_enrichment_hallucination_guard import (
    CatalogEnrichmentHallucinationGuard,
)
from app.services.catalog_enrichment_response_parser import ParsedCatalogEnrichment


class CatalogEnrichmentGroundingValidator:
    def __init__(self, guard: CatalogEnrichmentHallucinationGuard) -> None:
        self._guard = guard

    def validate(
        self,
        content: ParsedCatalogEnrichment,
        facts: TrustedCatalogFacts,
    ) -> EnrichmentValidationResult:
        known = {fact.fact_id for fact in facts.facts}
        referenced = {fact_id for item in content.all_items() for fact_id in item.fact_ids}
        issues: list[ClaimRiskCode] = []
        if not referenced or any(not item.fact_ids for item in content.all_items()):
            issues.append(ClaimRiskCode.UNGROUNDED_CONTENT)
        if not referenced.issubset(known):
            issues.append(ClaimRiskCode.UNKNOWN_FACT_REFERENCE)
        if not issues:
            issues.extend(self._guard.inspect(content, facts))
        warnings: list[EnrichmentWarningCode] = []
        attribute_facts = [fact for fact in facts.facts if fact.fact_id.startswith("ATTRIBUTE:")]
        if facts.warning_reason_codes:
            warnings.append(EnrichmentWarningCode.UPSTREAM_PROJECTION_WARNING)
        if len(attribute_facts) < 3:
            warnings.append(EnrichmentWarningCode.LIMITED_SOURCE_ATTRIBUTES)
        if any(fact.origin == "HUMAN_OVERRIDE" for fact in attribute_facts):
            warnings.append(EnrichmentWarningCode.HUMAN_OVERRIDE_PRESENT)
        if any(fact.validation_status == "VALID_WITH_WARNINGS" for fact in attribute_facts):
            warnings.append(EnrichmentWarningCode.VALIDATION_WARNING_PRESENT)
        if facts.description and "IDENTITY:description" not in referenced:
            warnings.append(EnrichmentWarningCode.ORIGINAL_DESCRIPTION_NOT_USED)
        if len(referenced & known) * 10_000 // len(known) < 5_000:
            warnings.append(EnrichmentWarningCode.LOW_FACT_COVERAGE)
        return EnrichmentValidationResult(
            valid=not issues,
            issue_codes=tuple(dict.fromkeys(issues)),
            warning_codes=tuple(dict.fromkeys(warnings)),
            grounded_fact_count=len(referenced & known),
            referenced_fact_count=len(referenced),
        )
