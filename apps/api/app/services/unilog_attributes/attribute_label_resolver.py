"""Map semantic names only to observed or explicitly approved official labels."""

import re

from app.domain.unilog_attributes import SemanticAttributeToObservedLabelMapping
from app.services.unilog_attributes.vocabulary_store import load_default_attribute_vocabulary


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


class UnilogAttributeLabelResolver:
    def __init__(self) -> None:
        vocabulary = load_default_attribute_vocabulary()
        self._labels = {item.normalized_label: item.label for item in vocabulary.observed_labels}
        self._semantic: dict[str, SemanticAttributeToObservedLabelMapping] = {
            _normalize(item.semantic_name): item for item in vocabulary.semantic_mappings
        }

    def resolve(self, semantic_name: str) -> tuple[str | None, int]:
        key = _normalize(semantic_name)
        exact = self._labels.get(key)
        if exact:
            return exact, 10_000
        mapping = self._semantic.get(key)
        if mapping and _normalize(mapping.observed_label) in self._labels:
            return mapping.observed_label, mapping.confidence_bp
        return None, 0
