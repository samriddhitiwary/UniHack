"""Conservative Decimal parsing, precision, and canonical string formatting."""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import cast

_DECIMAL = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


class NumericNormalizer:
    def __init__(self, *, max_decimal_places: int = 6) -> None:
        if isinstance(max_decimal_places, bool) or not 0 <= max_decimal_places <= 18:
            raise ValueError("max_decimal_places must be between 0 and 18")
        self._places = max_decimal_places

    def parse(self, raw_value: str) -> Decimal | None:
        value = raw_value.strip()
        if not _DECIMAL.fullmatch(value):
            return None
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            return None
        return parsed if parsed.is_finite() else None

    def round_conversion(self, value: Decimal) -> Decimal:
        exponent = cast(int, value.as_tuple().exponent)
        fractional_places = max(0, -exponent)
        if fractional_places <= self._places:
            return value
        quantum = Decimal(1).scaleb(-self._places)
        return value.quantize(quantum, rounding=ROUND_HALF_UP)

    @staticmethod
    def canonical(value: Decimal) -> str:
        if value == 0:
            return "0"
        rendered = format(value, "f")
        if "." in rendered:
            rendered = rendered.rstrip("0").rstrip(".")
        return rendered
