"""Position-sensitive and semantic attribute-triple evaluation."""

import re
from dataclasses import dataclass

from app.domain.unilog_challenge import UnilogDeliveryRecord
from app.domain.unilog_evaluation import UnilogAttributeMetrics


@dataclass(frozen=True, slots=True)
class _Triple:
    label: str
    value: str | None
    uom: str | None


def evaluate_attributes(
    pairs: tuple[tuple[UnilogDeliveryRecord, UnilogDeliveryRecord], ...],
) -> UnilogAttributeMetrics:
    expected_all: list[_Triple] = []
    actual_all: list[_Triple] = []
    position_exact = 0
    position_evaluable = 0
    for expected_record, actual_record in pairs:
        expected_values = expected_record.as_dict()
        actual_values = actual_record.as_dict()
        for index in range(1, 51):
            for prefix in ("ATTRIBUTE_LABEL", "ATTRIBUTE_VALUE", "ATTRIBUTE_UOM"):
                field = f"{prefix} {index}"
                expected_value = expected_values[field]
                actual_value = actual_values[field]
                if expected_value not in (None, ""):
                    position_evaluable += 1
                    if expected_value == actual_value:
                        position_exact += 1
        expected_all.extend(_triples(expected_record))
        actual_all.extend(_triples(actual_record))
    actual_by_label = {_key(item.label): item for item in actual_all}
    matched_labels = matched_values = matched_uoms = matched_triples = 0
    expected_uom_count = 0
    for expected_triple in expected_all:
        if expected_triple.uom is not None:
            expected_uom_count += 1
        actual_triple = actual_by_label.get(_key(expected_triple.label))
        if actual_triple is None:
            continue
        matched_labels += 1
        value_match = _optional_equal(expected_triple.value, actual_triple.value)
        uom_match = _optional_equal(expected_triple.uom, actual_triple.uom)
        if value_match:
            matched_values += 1
        if expected_triple.uom is not None and uom_match:
            matched_uoms += 1
        if value_match and uom_match:
            matched_triples += 1
    expected_count = len(expected_all)
    generated_count = len(actual_all)
    precision = _ratio(matched_triples, generated_count)
    recall = _ratio(matched_triples, expected_count)
    f1 = (
        2 * precision * recall // (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    return UnilogAttributeMetrics(
        expected_attribute_count=expected_count,
        generated_attribute_count=generated_count,
        matched_label_count=matched_labels,
        matched_value_count=matched_values,
        matched_uom_count=matched_uoms,
        matched_triple_count=matched_triples,
        position_exact_cell_count=position_exact,
        position_evaluable_cell_count=position_evaluable,
        precision_bp=precision,
        recall_bp=recall,
        f1_bp=f1,
        label_accuracy_bp=_ratio(matched_labels, expected_count),
        value_accuracy_bp=_ratio(matched_values, expected_count),
        uom_accuracy_bp=_ratio(matched_uoms, expected_uom_count),
        triple_accuracy_bp=_ratio(matched_triples, expected_count),
    )


def _triples(record: UnilogDeliveryRecord) -> tuple[_Triple, ...]:
    values = record.as_dict()
    triples = []
    for index in range(1, 51):
        label = values[f"ATTRIBUTE_LABEL {index}"]
        if label in (None, ""):
            continue
        value = values[f"ATTRIBUTE_VALUE {index}"]
        uom = values[f"ATTRIBUTE_UOM {index}"]
        triples.append(
            _Triple(
                label=str(label),
                value=None if value in (None, "") else str(value),
                uom=None if uom in (None, "") else str(uom),
            )
        )
    return tuple(triples)


def _key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _optional_equal(expected: str | None, actual: str | None) -> bool:
    if expected is None or actual is None:
        return expected is actual
    return _key(expected) == _key(actual)


def _ratio(numerator: int, denominator: int) -> int | None:
    return numerator * 10_000 // denominator if denominator else None
