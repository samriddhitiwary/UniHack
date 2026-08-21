"""Deterministic alignment, comparison, and observed-vocabulary derivation."""

import re
from collections import defaultdict
from collections.abc import Iterable

from app.domain.unilog_challenge import (
    AlignmentStatus,
    ComparisonStatus,
    FieldComparison,
    GroundTruthAlignment,
    ObservedVocabulary,
    UnilogChallengeInputRow,
    UnilogGroundTruthRecord,
)


def align_ground_truth(
    inputs: Iterable[UnilogChallengeInputRow],
    outputs: Iterable[UnilogGroundTruthRecord],
) -> tuple[GroundTruthAlignment, ...]:
    by_part: dict[str, list[str]] = defaultdict(list)
    for row in inputs:
        by_part[row.mfg_part_num].append(row.row_id)
    results = []
    for output in outputs:
        candidates = tuple(by_part.get(output.mfg_part_num, ()))
        status = (
            AlignmentStatus.NOT_FOUND
            if not candidates
            else AlignmentStatus.ALIGNED
            if len(candidates) == 1
            else AlignmentStatus.AMBIGUOUS_ALIGNMENT
        )
        results.append(
            GroundTruthAlignment(
                status=status,
                mfg_part_num=output.mfg_part_num,
                output_row_number=output.source_output_row_number,
                candidate_row_ids=candidates,
                aligned_input_row_id=candidates[0] if len(candidates) == 1 else None,
            )
        )
    return tuple(results)


def attach_alignments(
    outputs: Iterable[UnilogGroundTruthRecord],
    alignments: Iterable[GroundTruthAlignment],
) -> tuple[UnilogGroundTruthRecord, ...]:
    by_row = {item.output_row_number: item for item in alignments}
    return tuple(
        UnilogGroundTruthRecord(
            source_output_row_number=item.source_output_row_number,
            mfg_part_num=item.mfg_part_num,
            expected=item.expected,
            populated_fields=item.populated_fields,
            split=item.split,
            input_row_id=by_row[item.source_output_row_number].aligned_input_row_id,
        )
        for item in outputs
    )


def derive_observed_vocabulary(
    rows: Iterable[UnilogGroundTruthRecord],
) -> ObservedVocabulary:
    manufacturers: set[str] = set()
    brands: set[str] = set()
    classpaths: set[str] = set()
    labels: set[str] = set()
    uoms: set[str] = set()
    for row in rows:
        values = row.expected.as_dict()
        for target, bucket in (
            ("MANUFACTURER_NAME", manufacturers),
            ("BRAND_NAME", brands),
            ("Classpath", classpaths),
        ):
            value = values[target]
            if isinstance(value, str) and value:
                bucket.add(value)
        for index in range(1, 51):
            label = values[f"ATTRIBUTE_LABEL {index}"]
            uom = values[f"ATTRIBUTE_UOM {index}"]
            if isinstance(label, str) and label:
                labels.add(label)
            if isinstance(uom, str) and uom:
                uoms.add(uom)
    return ObservedVocabulary(
        manufacturers=frozenset(manufacturers),
        brands=frozenset(brands),
        classpaths=frozenset(classpaths),
        attribute_labels=frozenset(labels),
        uoms=frozenset(uoms),
    )


def compare_field(field_name: str, expected: str | None, actual: str | None) -> FieldComparison:
    if expected is None and actual is None:
        status = ComparisonStatus.BOTH_BLANK
    elif expected is None:
        status = ComparisonStatus.EXPECTED_BLANK
    elif actual is None:
        status = ComparisonStatus.ACTUAL_BLANK
    elif expected == actual:
        status = ComparisonStatus.EXACT_MATCH
    elif _comparison_key(expected) == _comparison_key(actual):
        status = ComparisonStatus.NORMALIZED_MATCH
    else:
        status = ComparisonStatus.MISMATCH
    return FieldComparison(
        field_name=field_name,
        expected_value=expected,
        actual_value=actual,
        status=status,
        normalization_method="unicode-casefold-whitespace"
        if status is ComparisonStatus.NORMALIZED_MATCH
        else None,
    )


def _comparison_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()
