"""Bounded helpers for exact delivery fields; no content generation."""

from collections.abc import Sequence

from app.domain.unilog_challenge import SourceReferences, UnilogAttributeCandidate


def map_attribute_candidates(
    attributes: Sequence[UnilogAttributeCandidate],
) -> dict[str, str | None]:
    if len(attributes) > 50:
        raise ValueError("at most 50 ordered Unilog attributes are supported")
    values: dict[str, str | None] = {}
    for index, item in enumerate(attributes, start=1):
        values[f"ATTRIBUTE_LABEL {index}"] = item.label
        values[f"ATTRIBUTE_VALUE {index}"] = item.normalized_value or item.raw_value
        values[f"ATTRIBUTE_UOM {index}"] = item.uom
    return values


def map_item_features(features: Sequence[str]) -> dict[str, str]:
    if len(features) > 20:
        raise ValueError("at most 20 ordered item features are supported")
    return {f"ITEM_FEATURES_{index}": value for index, value in enumerate(features, start=1)}


def map_source_references(references: SourceReferences) -> dict[str, str | None]:
    values: dict[str, str | None] = {"MFR URL": references.manufacturer_url}
    values.update(
        {f"Ref URL {index}": value for index, value in enumerate(references.reference_urls, 1)}
    )
    return values
