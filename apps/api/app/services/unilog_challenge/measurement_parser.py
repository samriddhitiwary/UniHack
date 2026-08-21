"""Exact trade-fraction and dimension parsing with source spans."""

import re
from fractions import Fraction

from app.domain.unilog_challenge import UnilogMeasurementCandidate

_NUMBER = r"(?:\d+-\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
_MEASUREMENT = re.compile(
    rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<unit>\"|in(?:ch(?:es)?)?)",
    re.IGNORECASE,
)
_DIMENSION = re.compile(
    rf"(?<![\w/])(?P<first>{_NUMBER})\s*(?P<first_unit>\")?\s*[xX\u00d7]\s*"
    rf"(?P<second>{_NUMBER})\s*(?P<second_unit>\")?"
)


def parse_trade_fraction(value: str) -> Fraction:
    """Parse integer, decimal, simple fraction, or hyphenated mixed fraction exactly."""
    cleaned = value.strip()
    if "-" in cleaned:
        whole, fraction = cleaned.split("-", 1)
        return Fraction(int(whole)) + Fraction(fraction)
    return Fraction(cleaned)


def parse_measurements(
    text: str, *, implicit_dimension_unit: str | None = None
) -> tuple[UnilogMeasurementCandidate, ...]:
    candidates: list[UnilogMeasurementCandidate] = []
    occupied: set[tuple[int, int]] = set()
    for match in _DIMENSION.finditer(text):
        units = (match.group("first_unit"), match.group("second_unit"))
        if not any(units) and implicit_dimension_unit is None:
            continue
        for name, unit in (("first", units[0]), ("second", units[1])):
            start, end = match.span(name)
            raw = match.group(name)
            normalized_unit = "in" if unit == '"' else implicit_dimension_unit or "in"
            candidates.append(
                UnilogMeasurementCandidate(
                    raw_text=raw + (unit or ""),
                    numeric_value=parse_trade_fraction(raw),
                    raw_unit=unit or "",
                    normalized_unit=normalized_unit,
                    evidence_span=(start, end + len(unit or "")),
                    confidence_bp=9_500 if unit else 8_500,
                )
            )
            occupied.add((start, end + len(unit or "")))
    for match in _MEASUREMENT.finditer(text):
        span = match.span()
        if any(start <= span[0] and span[1] <= end for start, end in occupied):
            continue
        unit = match.group("unit")
        candidates.append(
            UnilogMeasurementCandidate(
                raw_text=match.group(0),
                numeric_value=parse_trade_fraction(match.group("value")),
                raw_unit=unit,
                normalized_unit="in",
                evidence_span=span,
                confidence_bp=9_500,
            )
        )
    return tuple(sorted(candidates, key=lambda item: item.evidence_span))
