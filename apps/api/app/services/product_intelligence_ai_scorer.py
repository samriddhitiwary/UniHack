"""Optional grounded-AI quality component scoring."""

from app.domain.catalog_enrichment import CatalogEnrichmentResult
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceMetric,
)
from app.services.product_intelligence_policy import BASE_WEIGHTS


class ProductIntelligenceAiScorer:
    def score(
        self, enrichment: CatalogEnrichmentResult | None
    ) -> ProductIntelligenceComponentScore:
        base = BASE_WEIGHTS[ProductIntelligenceComponent.AI_GROUNDING_QUALITY]
        if enrichment is None:
            return ProductIntelligenceComponentScore(
                component=ProductIntelligenceComponent.AI_GROUNDING_QUALITY,
                status=ComponentEvaluationStatus.NOT_EVALUATED,
                raw_score_bp=None,
                base_weight_bp=base,
                normalized_weight_bp=0,
                weighted_contribution_bp=0,
                strength_codes=(),
                improvement_codes=("AI_ENRICHMENT_NOT_EVALUATED",),
                metrics=(),
            )
        raw = (
            enrichment.grounding_score_bp * 8_000 + enrichment.fact_coverage_bp * 2_000
        ) // 10_000
        return ProductIntelligenceComponentScore(
            component=ProductIntelligenceComponent.AI_GROUNDING_QUALITY,
            status=ComponentEvaluationStatus.EVALUATED,
            raw_score_bp=raw,
            base_weight_bp=base,
            normalized_weight_bp=0,
            weighted_contribution_bp=0,
            strength_codes=tuple(
                code
                for code, ok in (
                    ("AI_CONTENT_FULLY_GROUNDED", enrichment.grounding_score_bp == 10_000),
                    ("AI_FACT_COVERAGE_HIGH", enrichment.fact_coverage_bp >= 8_000),
                    ("AI_CONTENT_GENERATION_AVAILABLE", True),
                )
                if ok
            ),
            improvement_codes=("AI_FACT_COVERAGE_LOW",)
            if enrichment.fact_coverage_bp < 5_000
            else (),
            metrics=(
                ProductIntelligenceMetric(
                    name="aiGroundingScoreBp", value=enrichment.grounding_score_bp
                ),
                ProductIntelligenceMetric(
                    name="aiFactCoverageBp", value=enrichment.fact_coverage_bp
                ),
            ),
        )
