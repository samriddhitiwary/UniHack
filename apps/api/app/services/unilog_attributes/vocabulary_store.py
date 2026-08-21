"""Atomic JSON persistence and cached runtime loading."""

import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.unilog_attributes import (
    AttributeVocabularySource,
    SemanticAttributeToObservedLabelMapping,
    UnilogAttributeProductTypeRule,
    UnilogAttributeVocabulary,
    UnilogAttributeVocabularyStatistics,
    UnilogObservedAttributeDefinition,
    UnilogObservedUomResolution,
)

DEFAULT_ATTRIBUTE_VOCABULARY_PATH = (
    Path(__file__).parents[2] / "reference_data" / "unilog_attributes_v1.json"
)


def write_attribute_vocabulary(value: UnilogAttributeVocabulary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(asdict(value)), indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def load_attribute_vocabulary(path: Path) -> UnilogAttributeVocabulary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return UnilogAttributeVocabulary(
        policy_version=payload["policy_version"],
        input_sha256=payload["input_sha256"],
        ground_truth_sha256=payload["ground_truth_sha256"],
        artifact_hash=payload["artifact_hash"],
        observed_labels=tuple(
            UnilogObservedAttributeDefinition(
                **{
                    key: value
                    for key, value in item.items()
                    if key
                    not in {
                        "source",
                        "observed_values",
                        "observed_uoms",
                        "observed_product_types",
                    }
                },
                source=AttributeVocabularySource(item["source"]),
                observed_values=tuple(item["observed_values"]),
                observed_uoms=tuple(item["observed_uoms"]),
                observed_product_types=tuple(item["observed_product_types"]),
            )
            for item in payload["observed_labels"]
        ),
        observed_uoms=_load_uoms(payload["observed_uoms"]),
        normalization_mappings=_load_uoms(payload["normalization_mappings"]),
        semantic_mappings=tuple(
            SemanticAttributeToObservedLabelMapping(
                semantic_name=item["semantic_name"],
                observed_label=item["observed_label"],
                source=AttributeVocabularySource(item["source"]),
                confidence_bp=item["confidence_bp"],
            )
            for item in payload["semantic_mappings"]
        ),
        product_type_rules=tuple(
            UnilogAttributeProductTypeRule(
                product_type=item["product_type"],
                semantic_attributes=tuple(item["semantic_attributes"]),
                dimension_order=tuple(item["dimension_order"]),
                supports_quantity=item["supports_quantity"],
                supports_grit=item["supports_grit"],
                map_dimensions_to_size=item["map_dimensions_to_size"],
                priority=item["priority"],
            )
            for item in payload["product_type_rules"]
        ),
        statistics=UnilogAttributeVocabularyStatistics(**payload["statistics"]),
    )


def _load_uoms(items: list[dict[str, Any]]) -> tuple[UnilogObservedUomResolution, ...]:
    return tuple(
        UnilogObservedUomResolution(
            raw_uom=item["raw_uom"],
            normalized_uom=item["normalized_uom"],
            source=AttributeVocabularySource(item["source"]),
            confidence_bp=item["confidence_bp"],
            review_required=item["review_required"],
        )
        for item in items
    )


@lru_cache(maxsize=1)
def load_default_attribute_vocabulary() -> UnilogAttributeVocabulary:
    return load_attribute_vocabulary(DEFAULT_ATTRIBUTE_VOCABULARY_PATH)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
