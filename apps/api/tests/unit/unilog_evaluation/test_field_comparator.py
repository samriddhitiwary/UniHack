"""Field-aware comparison, groups, blank semantics, and accuracy rates."""

import pytest

from app.domain.unilog_evaluation import EvaluationMatchStatus, UnilogFieldGroup
from app.services.unilog_evaluation.field_comparator import (
    accuracy_metrics,
    compare_delivery_field,
    field_group,
)


def test_exact_and_safe_normalized_matches_remain_distinct() -> None:
    exact = compare_delivery_field("BRAND_NAME", "FRIGIDAIRE®", "FRIGIDAIRE®")
    normalized = compare_delivery_field("MANUFACTURER_NAME", "  Acme  Corp ", "acme corp")
    assert exact.status is EvaluationMatchStatus.EXACT_MATCH
    assert normalized.status is EvaluationMatchStatus.NORMALIZED_MATCH
    assert normalized.normalized_method is not None


def test_invoice_case_and_trademark_symbols_are_meaningful() -> None:
    invoice = compare_delivery_field("INVOICE_DESC", "DISHWASHER 120V", "dishwasher 120V")
    brand = compare_delivery_field("BRAND_NAME", "FRIGIDAIRE®", "frigidaire")
    assert invoice.status is EvaluationMatchStatus.MISMATCH
    assert brand.status is EvaluationMatchStatus.MISMATCH


@pytest.mark.parametrize(
    ("expected", "actual", "status"),
    [
        ("Value", None, EvaluationMatchStatus.EXPECTED_POPULATED_ACTUAL_BLANK),
        (None, "Value", EvaluationMatchStatus.EXPECTED_BLANK_ACTUAL_POPULATED),
        (None, None, EvaluationMatchStatus.BOTH_BLANK),
    ],
)
def test_blank_statuses_are_explicit(
    expected: str | None, actual: str | None, status: EvaluationMatchStatus
) -> None:
    assert compare_delivery_field("SHORT_DESC", expected, actual).status is status


def test_both_blank_never_inflates_accuracy() -> None:
    comparisons = (
        compare_delivery_field("BRAND_NAME", "Acme", "Acme"),
        compare_delivery_field("MFR URL", None, None),
        compare_delivery_field("UPC", None, None),
    )
    metrics = accuracy_metrics(comparisons)
    assert metrics.exact_match_count == 1
    assert metrics.both_blank_count == 2
    assert metrics.evaluable_field_count == 1
    assert metrics.exact_match_rate_bp == 10_000


def test_core_attribute_and_field_groups_are_explicit() -> None:
    attribute = compare_delivery_field("ATTRIBUTE_VALUE 4", "120", None)
    assert attribute.group is UnilogFieldGroup.ATTRIBUTE
    assert attribute.core_enrichment_field
    assert field_group("Product Image") is UnilogFieldGroup.ASSET
    assert field_group("Specification Sheet") is UnilogFieldGroup.DOCUMENT
    assert field_group("LENGTH") is UnilogFieldGroup.DIMENSION
    assert field_group("Country Of Origin") is UnilogFieldGroup.OTHER
