"""Assign resolved official attributes to deterministic delivery slots."""

from app.domain.unilog_challenge import UnilogSemanticAttributeCandidate
from app.services.unilog_attributes.rules import UnilogAttributeRuleRegistry


class UnilogAttributeDeliveryMapper:
    def __init__(self, rules: UnilogAttributeRuleRegistry | None = None) -> None:
        self._rules = rules or UnilogAttributeRuleRegistry()

    def assign_slots(
        self, attributes: tuple[UnilogSemanticAttributeCandidate, ...]
    ) -> tuple[tuple[int, UnilogSemanticAttributeCandidate], ...]:
        eligible = tuple(
            item for item in attributes if item.official_label and not item.review_required
        )
        used: set[int] = set()
        assigned: list[tuple[int, UnilogSemanticAttributeCandidate]] = []
        deferred = []
        for item in eligible:
            rule = self._rules.get(item.product_type)
            order = rule.semantic_attributes if rule else ()
            if item.official_label in order:
                slot = order.index(item.official_label) + 1
                if slot <= 50 and slot not in used:
                    assigned.append((slot, item))
                    used.add(slot)
                    continue
            deferred.append(item)
        available = (slot for slot in range(1, 51) if slot not in used)
        for item, slot in zip(deferred, available, strict=False):
            assigned.append((slot, item))
        return tuple(sorted(assigned, key=lambda pair: pair[0]))
