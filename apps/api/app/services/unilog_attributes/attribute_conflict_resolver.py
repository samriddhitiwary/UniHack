"""Deterministic duplicate collapse and conservative conflict marking."""

from dataclasses import replace

from app.domain.unilog_attributes import AttributeReviewReason
from app.domain.unilog_challenge import UnilogSemanticAttributeCandidate


def resolve_attribute_conflicts(
    candidates: tuple[UnilogSemanticAttributeCandidate, ...],
) -> tuple[UnilogSemanticAttributeCandidate, ...]:
    retained: dict[tuple[str, str, str | None], UnilogSemanticAttributeCandidate] = {}
    by_semantic: dict[str, set[tuple[str, str | None]]] = {}
    for item in candidates:
        key = (item.semantic_name, item.normalized_value, item.uom)
        retained.setdefault(key, item)
        by_semantic.setdefault(item.semantic_name, set()).add((item.normalized_value, item.uom))
    results = []
    for item in retained.values():
        conflict = len(by_semantic[item.semantic_name]) > 1
        reasons = item.review_reasons
        if conflict and AttributeReviewReason.ATTRIBUTE_CONFLICT not in reasons:
            reasons = (*reasons, AttributeReviewReason.ATTRIBUTE_CONFLICT)
        results.append(
            replace(item, review_required=item.review_required or conflict, review_reasons=reasons)
        )
    return tuple(results)
