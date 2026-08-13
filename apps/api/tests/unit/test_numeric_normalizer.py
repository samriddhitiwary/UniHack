from decimal import Decimal

from app.services.numeric_normalizer import NumericNormalizer


def test_decimal_parse_and_canonical_formatting() -> None:
    normalizer = NumericNormalizer()
    assert [
        normalizer.canonical(normalizer.parse(value))
        for value in ("5.5000", "+415.0", "-0.0", "-2.5")
    ] == ["5.5", "415", "0", "-2.5"]


def test_malformed_and_decimal_comma_are_rejected() -> None:
    normalizer = NumericNormalizer()
    assert all(normalizer.parse(value) is None for value in ("5..5", "5k", "five", "5,5", "1e3"))


def test_conversion_precision_uses_half_up_only_when_needed() -> None:
    normalizer = NumericNormalizer(max_decimal_places=6)
    assert normalizer.canonical(normalizer.round_conversion(Decimal("7.45699872"))) == "7.456999"
    assert normalizer.round_conversion(Decimal("5.5")) == Decimal("5.5")
