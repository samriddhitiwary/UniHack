"""Strict validation boundary for optional model-suggested product types."""

import json

from app.domain.unilog_classification import (
    ClassificationReviewReason,
    ProductTypeMatchMethod,
    UnilogProductTypeResolution,
)


def validate_model_product_type_proposal(
    description: str, response: str
) -> UnilogProductTypeResolution | None:
    try:
        payload = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or set(payload) != {"productType", "evidenceText"}:
        return None
    product_type, evidence = payload["productType"], payload["evidenceText"]
    if (
        not isinstance(product_type, str)
        or not isinstance(evidence, str)
        or not product_type.strip()
    ):
        return None
    start = description.find(evidence)
    if start < 0 or product_type.casefold() not in evidence.casefold():
        return None
    return UnilogProductTypeResolution(
        product_type=product_type.strip(),
        product_family=None,
        match_method=ProductTypeMatchMethod.MODEL_ASSISTED,
        evidence_span=(start, start + len(evidence)),
        evidence_text=evidence,
        confidence_bp=6_000,
        review_required=True,
        review_reasons=(ClassificationReviewReason.CLASSPATH_UNKNOWN,),
        candidate_product_types=(product_type.strip(),),
    )
