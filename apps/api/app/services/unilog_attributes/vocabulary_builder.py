"""Deterministic observed attribute vocabulary construction."""

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict
from typing import Any

from app.domain.unilog_attributes import (
    MAX_ATTRIBUTE_EVIDENCE_VALUES,
    UNILOG_ATTRIBUTE_POLICY_VERSION,
    AttributeVocabularySource,
    UnilogAttributeVocabulary,
    UnilogAttributeVocabularyStatistics,
    UnilogObservedAttributeDefinition,
    UnilogObservedUomResolution,
)
from app.domain.unilog_challenge import UnilogChallengeInputRow, UnilogGroundTruthRecord
from app.services.unilog_attributes.policy import (
    SEMANTIC_LABEL_MAPPINGS,
    UOM_NORMALIZATION_MAPPINGS,
)
from app.services.unilog_attributes.rules import PRODUCT_TYPE_ATTRIBUTE_RULES
from app.services.unilog_classification.product_type_resolver import UnilogProductTypeResolver


def normalize_attribute_label(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def build_attribute_vocabulary(
    rows: Iterable[UnilogChallengeInputRow],
    truth_rows: Iterable[UnilogGroundTruthRecord],
    *,
    input_sha256: str,
    ground_truth_sha256: str,
) -> UnilogAttributeVocabulary:
    inputs = tuple(rows)
    truths = tuple(truth_rows)
    by_id = {row.row_id: row for row in inputs}
    resolver = UnilogProductTypeResolver()
    values: dict[str, set[str]] = defaultdict(set)
    uoms: dict[str, set[str]] = defaultdict(set)
    product_types: dict[str, set[str]] = defaultdict(set)
    support: dict[str, int] = defaultdict(int)
    labels_by_key: dict[str, str] = {}
    observed_uom_values: set[str] = set()
    for truth in truths:
        input_row = by_id.get(truth.input_row_id or "")
        product_type = (
            resolver.resolve(input_row.part_desc).product_type if input_row is not None else None
        )
        for index in range(1, 51):
            label_value = truth.expected.value(f"ATTRIBUTE_LABEL {index}")
            if not isinstance(label_value, str) or not label_value.strip():
                continue
            label = label_value.strip()
            key = normalize_attribute_label(label)
            labels_by_key[key] = label
            support[key] += 1
            raw_value = truth.expected.value(f"ATTRIBUTE_VALUE {index}")
            raw_uom = truth.expected.value(f"ATTRIBUTE_UOM {index}")
            if isinstance(raw_value, str) and raw_value.strip():
                values[key].add(raw_value.strip())
            if isinstance(raw_uom, str) and raw_uom.strip():
                uoms[key].add(raw_uom.strip())
                observed_uom_values.add(raw_uom.strip())
            if product_type:
                product_types[key].add(product_type)
    definitions = tuple(
        UnilogObservedAttributeDefinition(
            label=labels_by_key[key],
            normalized_label=key,
            observed_values=tuple(sorted(values[key]))[:MAX_ATTRIBUTE_EVIDENCE_VALUES],
            observed_uoms=tuple(sorted(uoms[key])),
            observed_product_types=tuple(sorted(product_types[key])),
            support_count=support[key],
            source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
        )
        for key in sorted(labels_by_key)
    )
    observed_uoms = tuple(
        UnilogObservedUomResolution(
            raw_uom=value,
            normalized_uom=value,
            source=AttributeVocabularySource.OBSERVED_LABELLED_OUTPUT,
            confidence_bp=10_000,
            review_required=False,
        )
        for value in sorted(observed_uom_values, key=str.casefold)
    )
    statistics = UnilogAttributeVocabularyStatistics(
        input_rows=len(inputs),
        labelled_rows=len(truths),
        observed_labels=len(definitions),
        observed_uoms=len(observed_uoms),
        semantic_mappings=len(SEMANTIC_LABEL_MAPPINGS),
        product_type_rules=len(PRODUCT_TYPE_ATTRIBUTE_RULES),
    )
    hash_payload = {
        "observedLabels": [asdict(item) for item in definitions],
        "observedUoms": [asdict(item) for item in observed_uoms],
        "normalizationMappings": [asdict(item) for item in UOM_NORMALIZATION_MAPPINGS],
        "semanticMappings": [asdict(item) for item in SEMANTIC_LABEL_MAPPINGS],
        "productTypeRules": [asdict(item) for item in PRODUCT_TYPE_ATTRIBUTE_RULES],
        "statistics": asdict(statistics),
    }
    artifact_hash = hashlib.sha256(
        json.dumps(_jsonable(hash_payload), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return UnilogAttributeVocabulary(
        policy_version=UNILOG_ATTRIBUTE_POLICY_VERSION,
        input_sha256=input_sha256,
        ground_truth_sha256=ground_truth_sha256,
        artifact_hash=artifact_hash,
        observed_labels=definitions,
        observed_uoms=observed_uoms,
        normalization_mappings=UOM_NORMALIZATION_MAPPINGS,
        semantic_mappings=SEMANTIC_LABEL_MAPPINGS,
        product_type_rules=PRODUCT_TYPE_ATTRIBUTE_RULES,
        statistics=statistics,
    )


def _jsonable(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
