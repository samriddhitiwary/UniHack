"""Product-type-aware, evidence-grounded semantic attribute extraction."""

import re
from dataclasses import replace

from app.domain.unilog_attributes import AttributeExtractionMethod, AttributeReviewReason
from app.domain.unilog_challenge import (
    ObservedVocabulary,
    UnilogDescriptionSignals,
    UnilogSemanticAttributeCandidate,
)
from app.services.unilog_attributes.attribute_conflict_resolver import (
    resolve_attribute_conflicts,
)
from app.services.unilog_attributes.attribute_label_resolver import UnilogAttributeLabelResolver
from app.services.unilog_attributes.rules import UnilogAttributeRuleRegistry
from app.services.unilog_attributes.unit_normalizer import normalize_observed_uom

_NUMBER = r"(?:\d+-\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"
_QUANTITY = re.compile(
    r"(?<!\w)(?P<value>\d+)\s*(?P<unit>pc|pcs|piece|pieces|pack|ea|disc/box|/box)\b",
    re.IGNORECASE,
)
_GRIT = re.compile(r"(?<!\w)P(?P<value>\d{2,4})(?!\w)", re.IGNORECASE)
_MATERIAL = re.compile(
    r"\b(?P<value>stainless\s+steel|SST|SS|brass|aluminum|steel|PVC|copper)\b",
    re.IGNORECASE,
)
_SCALARS = (
    ("Voltage Rating", re.compile(rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<uom>V)\b", re.I)),
    ("Amperage Rating", re.compile(rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<uom>A)\b", re.I)),
    ("Sound Level", re.compile(rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<uom>dBA)\b", re.I)),
    ("Pressure", re.compile(rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<uom>PSI)\b", re.I)),
    ("Horsepower", re.compile(rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<uom>HP)\b", re.I)),
    ("Frequency", re.compile(rf"(?<![\w/])(?P<value>{_NUMBER})\s*(?P<uom>Hz)\b", re.I)),
)
_GENERIC_PRIORITY = (
    "Series",
    "Material",
    "Dimensions",
    "Voltage Rating",
    "Amperage Rating",
    "Sound Level",
    "Grit",
    "Package Quantity",
    "Package Unit",
    "Pressure",
    "Horsepower",
    "Frequency",
)


class UnilogAttributeExtractor:
    def __init__(
        self,
        *,
        labels: UnilogAttributeLabelResolver | None = None,
        rules: UnilogAttributeRuleRegistry | None = None,
    ) -> None:
        self._labels = labels or UnilogAttributeLabelResolver()
        self._rules = rules or UnilogAttributeRuleRegistry()

    def extract(
        self, signals: UnilogDescriptionSignals, vocabulary: ObservedVocabulary | None
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        del vocabulary  # Official label lookup comes only from the persisted SPEC-045 artifact.
        product_type = signals.product_type
        rule = self._rules.get(product_type)
        candidates: list[UnilogSemanticAttributeCandidate] = []
        if signals.series is not None and signals.series_span is not None:
            candidates.append(
                self._candidate(
                    "Series", signals.series, signals.series, None, signals.series_span, signals
                )
            )
        candidates.extend(self._materials(signals))
        candidates.extend(self._scalars(signals))
        quantity_matches = tuple(_QUANTITY.finditer(signals.source_text))
        if rule is None or rule.supports_quantity:
            for match in quantity_matches:
                candidates.append(
                    self._candidate(
                        "Package Quantity",
                        match.group("value"),
                        match.group("value"),
                        None,
                        match.span("value"),
                        signals,
                    )
                )
                candidates.append(
                    self._candidate(
                        "Package Unit",
                        match.group("unit"),
                        match.group("unit"),
                        None,
                        match.span("unit"),
                        signals,
                    )
                )
        if rule is not None and rule.supports_grit:
            for match in _GRIT.finditer(signals.source_text):
                candidates.append(
                    self._candidate(
                        "Grit",
                        match.group(0),
                        match.group(0).upper(),
                        None,
                        match.span(),
                        signals,
                        method=AttributeExtractionMethod.PRODUCT_TYPE_RULE,
                    )
                )
        candidates.extend(self._dimensions(signals, rule.dimension_order if rule else ()))
        explicit_dimension_unit = any(item.raw_unit for item in signals.measurements)
        map_dimensions = bool(rule and rule.map_dimensions_to_size) or explicit_dimension_unit
        if map_dimensions and len(signals.measurements) >= 2:
            start = signals.measurements[0].evidence_span[0]
            end = signals.measurements[-1].evidence_span[1]
            source = signals.source_text[start:end]
            candidates.append(
                self._candidate(
                    "Dimensions",
                    source,
                    source,
                    None,
                    (start, end),
                    signals,
                    method=AttributeExtractionMethod.PRODUCT_TYPE_RULE,
                )
            )
        resolved = list(resolve_attribute_conflicts(tuple(candidates)))
        resolved.sort(key=lambda item: self._sort_key(item, rule.dimension_order if rule else ()))
        if len(resolved) > 50:
            resolved = resolved[:50]
            resolved[-1] = replace(
                resolved[-1],
                review_required=True,
                review_reasons=(
                    *resolved[-1].review_reasons,
                    AttributeReviewReason.ATTRIBUTE_OVERFLOW,
                ),
            )
        return tuple(resolved)

    @staticmethod
    def _deduplicate(
        candidates: tuple[UnilogSemanticAttributeCandidate, ...],
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        """Compatibility entry point for the shared conflict resolver."""

        return resolve_attribute_conflicts(candidates)

    def _candidate(
        self,
        name: str,
        raw_value: str,
        normalized_value: str,
        raw_uom: str | None,
        span: tuple[int, int],
        signals: UnilogDescriptionSignals,
        *,
        method: AttributeExtractionMethod = AttributeExtractionMethod.EXPLICIT_PATTERN,
        confidence_bp: int = 9_500,
    ) -> UnilogSemanticAttributeCandidate:
        official, mapping_confidence = self._labels.resolve(name)
        normalized_uom = normalize_observed_uom(raw_uom) if raw_uom else None
        reasons: tuple[AttributeReviewReason, ...] = ()
        if official is None:
            reasons = (AttributeReviewReason.ATTRIBUTE_LABEL_UNKNOWN,)
        if raw_uom and normalized_uom is None:
            reasons = (*reasons, AttributeReviewReason.ATTRIBUTE_UNIT_AMBIGUOUS)
        confidence = min(confidence_bp, mapping_confidence) if official else confidence_bp
        fact_name = "".join(char for char in name.title() if char.isalnum())
        source = signals.source_text[span[0] : span[1]]
        return UnilogSemanticAttributeCandidate(
            semantic_name=name,
            raw_value=raw_value,
            normalized_value=normalized_value,
            uom=normalized_uom,
            evidence_span=span,
            fact_id=f"ATTRIBUTE:{fact_name}:{span[0]}",
            official_label=official,
            confidence_bp=confidence,
            review_required=raw_uom is not None and normalized_uom is None,
            raw_uom=raw_uom,
            source_text=source,
            source_start=span[0],
            source_end=span[1],
            product_type=signals.product_type,
            method=method,
            review_reasons=reasons,
        )

    def _materials(
        self, signals: UnilogDescriptionSignals
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        results = []
        for match in _MATERIAL.finditer(signals.source_text):
            raw = match.group("value")
            normalized = (
                "Stainless Steel"
                if raw.casefold() in {"ss", "sst", "stainless steel"}
                else raw.title()
            )
            results.append(
                self._candidate("Material", raw, normalized, None, match.span(), signals)
            )
        return tuple(results)

    def _scalars(
        self, signals: UnilogDescriptionSignals
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        results = []
        for semantic, pattern in _SCALARS:
            for match in pattern.finditer(signals.source_text):
                results.append(
                    self._candidate(
                        semantic,
                        match.group("value"),
                        match.group("value"),
                        match.group("uom"),
                        match.span(),
                        signals,
                    )
                )
        return tuple(results)

    def _dimensions(
        self, signals: UnilogDescriptionSignals, dimension_order: tuple[str, ...]
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        known = len(dimension_order) == len(signals.measurements)
        results = []
        for index, measurement in enumerate(signals.measurements):
            semantic = dimension_order[index] if known else f"Dimension {index + 1}"
            item = self._candidate(
                semantic,
                measurement.raw_text,
                measurement.exact_value,
                measurement.raw_unit or measurement.normalized_unit,
                measurement.evidence_span,
                signals,
                method=(
                    AttributeExtractionMethod.PRODUCT_TYPE_RULE
                    if known
                    else AttributeExtractionMethod.MEASUREMENT_PARSE
                ),
                confidence_bp=measurement.confidence_bp,
            )
            if not known:
                item = replace(
                    item,
                    review_reasons=(
                        *item.review_reasons,
                        AttributeReviewReason.ATTRIBUTE_TYPE_CONTEXT_REQUIRED,
                    ),
                )
            results.append(item)
        return tuple(results)

    @staticmethod
    def _sort_key(
        item: UnilogSemanticAttributeCandidate, dimension_order: tuple[str, ...]
    ) -> tuple[int, int, str]:
        preferred = (*dimension_order, *_GENERIC_PRIORITY)
        rank = (
            preferred.index(item.semantic_name)
            if item.semantic_name in preferred
            else len(preferred)
        )
        return rank, item.evidence_span[0], item.semantic_name
