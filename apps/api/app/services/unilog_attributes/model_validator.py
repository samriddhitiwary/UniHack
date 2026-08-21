"""Strict evidence validation for optional model semantic candidates."""

import json
from fractions import Fraction

from app.domain.unilog_attributes import AttributeExtractionMethod, AttributeReviewReason
from app.domain.unilog_challenge import UnilogSemanticAttributeCandidate
from app.services.unilog_attributes.attribute_label_resolver import UnilogAttributeLabelResolver
from app.services.unilog_attributes.unit_normalizer import normalize_observed_uom


def validate_model_attribute_candidates(
    description: str, response: str, *, product_type: str | None = None
) -> tuple[UnilogSemanticAttributeCandidate, ...]:
    try:
        payload = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return ()
    if not isinstance(payload, dict) or set(payload) != {"attributes"}:
        return ()
    attributes = payload["attributes"]
    if not isinstance(attributes, list) or len(attributes) > 50:
        return ()
    labels = UnilogAttributeLabelResolver()
    results: list[UnilogSemanticAttributeCandidate] = []
    for item in attributes:
        if not isinstance(item, dict) or set(item) != {
            "semanticName",
            "value",
            "uom",
            "evidenceText",
        }:
            continue
        semantic, value, raw_uom, evidence = (
            item["semanticName"],
            item["value"],
            item["uom"],
            item["evidenceText"],
        )
        if not all(isinstance(value, str) for value in (semantic, value, raw_uom, evidence)):
            continue
        start = description.find(evidence)
        if start < 0 or not _value_supported(value, evidence):
            continue
        normalized_uom = normalize_observed_uom(raw_uom) if raw_uom else None
        if raw_uom and normalized_uom is None:
            continue
        official, mapping_confidence = labels.resolve(semantic)
        reasons = () if official else (AttributeReviewReason.ATTRIBUTE_LABEL_UNKNOWN,)
        results.append(
            UnilogSemanticAttributeCandidate(
                semantic_name=semantic,
                raw_value=value,
                normalized_value=value,
                uom=normalized_uom,
                evidence_span=(start, start + len(evidence)),
                fact_id=f"ATTRIBUTE:Model:{len(results) + 1}",
                official_label=official,
                confidence_bp=min(6_500, mapping_confidence) if official else 6_000,
                raw_uom=raw_uom or None,
                source_text=evidence,
                source_start=start,
                source_end=start + len(evidence),
                product_type=product_type,
                method=AttributeExtractionMethod.MODEL_ASSISTED,
                review_reasons=reasons,
            )
        )
    return tuple(results)


def _value_supported(value: str, evidence: str) -> bool:
    if value.casefold() in evidence.casefold():
        return True
    try:
        return Fraction(value) == Fraction(evidence.strip().split()[0].replace('"', ""))
    except (ValueError, ZeroDivisionError):
        return False
