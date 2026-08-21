"""Bounded deterministic signal extraction from organizer descriptions."""

import re

from app.domain.unilog_challenge import UnilogChallengeInputRow, UnilogDescriptionSignals
from app.services.unilog_challenge.measurement_parser import parse_measurements
from app.services.unilog_classification.product_type_resolver import UnilogProductTypeResolver

_QUANTITY = re.compile(r"(?<!\w)(?P<count>\d+)\s*(?:pc|pcs|piece|pieces|disc/box)\b", re.I)
_GRIT = re.compile(r"(?<!\w)P(?P<grit>\d{2,4})(?!\w)", re.I)
_SERIES = re.compile(r"\b(?P<series>[A-Za-z0-9][A-Za-z0-9 -]{0,30}\sSeries)\b", re.I)
_STAINLESS = re.compile(r"\b(?:SS|SST|stainless\s+steel)\b", re.I)


class UnilogDescriptionSignalExtractor:
    def __init__(self, resolver: UnilogProductTypeResolver | None = None) -> None:
        self._resolver = resolver or UnilogProductTypeResolver()

    def extract(self, row: UnilogChallengeInputRow) -> UnilogDescriptionSignals:
        text = row.part_desc
        resolution = self._resolver.resolve(text)
        product_type = resolution.product_type
        product_span = resolution.evidence_span
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
            product_type_resolution=resolution,
            source_text=text,
        )
