"""Bounded deterministic signal extraction from organizer descriptions."""

import re

from app.domain.unilog_challenge import UnilogChallengeInputRow, UnilogDescriptionSignals
from app.services.unilog_challenge.measurement_parser import parse_measurements

_PRODUCT_TYPES = (
    "sanding belt",
    "stikit film",
    "dishwasher",
    "coupling",
    "faucet",
    "sanding disc",
    "abrasive disc",
    "drill bit",
    "filter",
    "valve",
    "pump",
    "motor",
)
_QUANTITY = re.compile(r"(?<!\w)(?P<count>\d+)\s*(?:pc|pcs|piece|pieces|disc/box)\b", re.I)
_GRIT = re.compile(r"(?<!\w)P(?P<grit>\d{2,4})(?!\w)", re.I)
_SERIES = re.compile(r"\b(?P<series>[A-Za-z0-9][A-Za-z0-9 -]{0,30}\sSeries)\b", re.I)
_STAINLESS = re.compile(r"\b(?:SS|SST|stainless\s+steel)\b", re.I)


class UnilogDescriptionSignalExtractor:
    def extract(self, row: UnilogChallengeInputRow) -> UnilogDescriptionSignals:
        text = row.part_desc
        lowered = text.casefold()
        product_type: str | None = None
        product_span: tuple[int, int] | None = None
        for phrase in _PRODUCT_TYPES:
            start = lowered.find(phrase)
            if start >= 0:
                product_type = phrase.title()
                product_span = (start, start + len(phrase))
                break
        implicit_unit = "in" if product_type == "Sanding Belt" else None
        quantity = _QUANTITY.search(text)
        grit = _GRIT.search(text)
        series = _SERIES.search(text)
        material = _STAINLESS.search(text)
        return UnilogDescriptionSignals(
            product_type=product_type,
            product_type_span=product_span,
            series=series.group("series") if series else None,
            series_span=series.span() if series else None,
            measurements=parse_measurements(text, implicit_dimension_unit=implicit_unit),
            quantity=int(quantity.group("count")) if quantity else None,
            quantity_span=quantity.span() if quantity else None,
            grit=f"P{grit.group('grit')}" if grit else None,
            grit_span=grit.span() if grit else None,
            material="Stainless Steel" if material else None,
            material_span=material.span() if material else None,
        )
