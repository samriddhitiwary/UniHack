"""Distinct-source corroboration component scoring."""

from app.core.exceptions import ProductIntelligenceRequiredComponentInvalidError
from app.domain.attribute_selection import AttributeSelectionResult
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceMetric,
)
from app.domain.reviewed_attributes import FinalAttributeOrigin, FinalReviewedAttributeSet
from app.services.product_intelligence_policy import BASE_WEIGHTS, weighted_mean


class ProductIntelligenceCorroborationScorer:
    def score(
        self, materialization: FinalReviewedAttributeSet, selection: AttributeSelectionResult
    ) -> ProductIntelligenceComponentScore:
        selected = {item.attribute_name: item for item in selection.attributes}
        values = []
        single = required_single = required_weak = multi = three = overrides = 0
        for attribute in materialization.attributes:
            selected_attribute = selected.get(attribute.attribute_name)
            if selected_attribute is None:
                raise ProductIntelligenceRequiredComponentInvalidError()
            source_count = (
                0
                if attribute.origin is FinalAttributeOrigin.HUMAN_OVERRIDE
                else selected_attribute.distinct_source_count
            )
            points = (
                5_000
                if source_count == 0
                else 6_000
                if source_count == 1
                else 9_000
                if source_count == 2
                else 10_000
            )
            values.append((points, 2 if attribute.required else 1))
            single += source_count == 1
            required_single += attribute.required and source_count == 1
            required_weak += attribute.required and source_count < 2
            multi += source_count >= 2
            three += source_count >= 3
            overrides += source_count == 0
        raw = weighted_mean(tuple(values))
        return ProductIntelligenceComponentScore(
            component=ProductIntelligenceComponent.SOURCE_CORROBORATION,
            status=ComponentEvaluationStatus.EVALUATED,
            raw_score_bp=raw,
            base_weight_bp=BASE_WEIGHTS[ProductIntelligenceComponent.SOURCE_CORROBORATION],
            normalized_weight_bp=0,
            weighted_contribution_bp=0,
            strength_codes=tuple(
                code
                for code, ok in (
                    ("MULTI_SOURCE_SUPPORT_HIGH", multi * 2 >= len(values)),
                    ("ALL_REQUIRED_ATTRIBUTES_CORROBORATED", not required_weak),
                    ("THREE_PLUS_SOURCE_SUPPORT_PRESENT", bool(three)),
                )
                if ok
            ),
            improvement_codes=tuple(
                code
                for code, ok in (
                    ("SINGLE_SOURCE_ATTRIBUTES_PRESENT", bool(single)),
                    ("REQUIRED_ATTRIBUTE_SINGLE_SOURCE", bool(required_single)),
                    ("HUMAN_OVERRIDE_WITHOUT_SOURCE_CORROBORATION", bool(overrides)),
                )
                if ok
            ),
            metrics=(
                ProductIntelligenceMetric(name="singleSourceAttributeCount", value=single),
                ProductIntelligenceMetric(
                    name="requiredSingleSourceAttributeCount", value=required_single
                ),
                ProductIntelligenceMetric(name="multiSourceAttributeCount", value=multi),
                ProductIntelligenceMetric(name="threePlusSourceAttributeCount", value=three),
            ),
        )
