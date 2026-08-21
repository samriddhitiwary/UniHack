"""Evidence-backed, deliberately small UOM normalization."""

from app.domain.unilog_attributes import UnilogObservedUomResolution
from app.services.unilog_attributes.vocabulary_store import load_default_attribute_vocabulary


class UnilogObservedUnitNormalizer:
    def __init__(self) -> None:
        vocabulary = load_default_attribute_vocabulary()
        self._by_raw = {item.raw_uom.casefold(): item for item in vocabulary.normalization_mappings}

    def resolve(self, raw_uom: str) -> UnilogObservedUomResolution | None:
        return self._by_raw.get(raw_uom.strip().casefold())


def normalize_observed_uom(raw_uom: str) -> str | None:
    resolved = UnilogObservedUnitNormalizer().resolve(raw_uom)
    return resolved.normalized_uom if resolved else None
