"""Decimal exact and zero-safe tolerance comparison."""

from decimal import Decimal, InvalidOperation


class AttributeNumericComparator:
    def __init__(
        self, *, relative_tolerance_bp: int = 50, absolute_tolerance: str = "0.000001"
    ) -> None:
        if not 0 <= relative_tolerance_bp <= 10_000:
            raise ValueError("relative_tolerance_bp must be between 0 and 10000")
        try:
            absolute = Decimal(absolute_tolerance)
        except InvalidOperation as exc:
            raise ValueError("absolute_tolerance must be a Decimal string") from exc
        if not absolute.is_finite() or absolute < 0:
            raise ValueError("absolute_tolerance must be finite and non-negative")
        self._relative = Decimal(relative_tolerance_bp) / Decimal(10_000)
        self._absolute = absolute

    @staticmethod
    def parse(value: str) -> Decimal | None:
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            return None
        return parsed if parsed.is_finite() else None

    def compare(self, left: Decimal, right: Decimal, *, integer: bool = False) -> str:
        if left == right:
            return "EXACT"
        if integer:
            return "DIFFERENT"
        difference = abs(left - right)
        if difference <= self._absolute:
            return "TOLERANCE"
        denominator = max(abs(left), abs(right))
        if denominator != 0 and difference / denominator <= self._relative:
            return "TOLERANCE"
        return "DIFFERENT"
