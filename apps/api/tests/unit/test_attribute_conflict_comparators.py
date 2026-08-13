from decimal import Decimal

from app.services.attribute_numeric_comparator import AttributeNumericComparator
from app.services.attribute_text_comparator import text_comparison_form


def test_decimal_comparator_uses_exact_absolute_relative_and_conflict_rules() -> None:
    comparator = AttributeNumericComparator(relative_tolerance_bp=50, absolute_tolerance="0.000001")
    assert comparator.compare(Decimal("1"), Decimal("1")) == "EXACT"
    assert comparator.compare(Decimal("0"), Decimal("0.0000005")) == "TOLERANCE"
    assert comparator.compare(Decimal("100"), Decimal("100.4")) == "TOLERANCE"
    assert comparator.compare(Decimal("100"), Decimal("101")) == "DIFFERENT"
    assert comparator.compare(Decimal("1"), Decimal("1.0"), integer=True) == "EXACT"
    assert comparator.parse("not-a-number") is None


def test_text_form_collapses_whitespace_and_case_only() -> None:
    assert text_comparison_form("  Cast   IRON ") == "cast iron"
    assert text_comparison_form("cast-iron") != text_comparison_form("cast iron")
