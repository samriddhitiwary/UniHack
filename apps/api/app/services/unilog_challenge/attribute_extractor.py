"""Extract grounded semantic attributes and only assign observed official labels."""

from app.domain.unilog_challenge import (
    ObservedVocabulary,
    UnilogDescriptionSignals,
    UnilogSemanticAttributeCandidate,
)


class UnilogAttributeExtractor:
    def extract(
        self, signals: UnilogDescriptionSignals, vocabulary: ObservedVocabulary | None
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        observed = frozenset() if vocabulary is None else vocabulary.attribute_labels
        candidates: list[UnilogSemanticAttributeCandidate] = []
        if signals.series is not None and signals.series_span is not None:
            candidates.append(
                self._candidate("Series", signals.series, None, signals.series_span, observed)
            )
        if signals.material is not None and signals.material_span is not None:
            candidates.append(
                self._candidate("Material", signals.material, None, signals.material_span, observed)
            )
        if signals.quantity is not None and signals.quantity_span is not None:
            candidates.append(
                self._candidate(
                    "Package Quantity",
                    str(signals.quantity),
                    None,
                    signals.quantity_span,
                    observed,
                )
            )
        if signals.grit is not None and signals.grit_span is not None:
            candidates.append(
                self._candidate("Grit", signals.grit, None, signals.grit_span, observed)
            )
        for index, measurement in enumerate(signals.measurements):
            semantic = (
                ("Width", "Length")[index] if len(signals.measurements) == 2 else "Measurement"
            )
            candidates.append(
                self._candidate(
                    semantic,
                    measurement.exact_value,
                    measurement.normalized_unit,
                    measurement.evidence_span,
                    observed,
                )
            )
        return self._deduplicate(tuple(candidates))

    @staticmethod
    def _candidate(
        name: str,
        value: str,
        uom: str | None,
        span: tuple[int, int],
        observed: frozenset[str],
    ) -> UnilogSemanticAttributeCandidate:
        fact_name = "".join(char for char in name.title() if char.isalnum())
        return UnilogSemanticAttributeCandidate(
            semantic_name=name,
            raw_value=value,
            normalized_value=value,
            uom=uom,
            evidence_span=span,
            fact_id=f"ATTRIBUTE:{fact_name}",
            official_label=name if name in observed else None,
            confidence_bp=9_000,
        )

    @staticmethod
    def _deduplicate(
        candidates: tuple[UnilogSemanticAttributeCandidate, ...],
    ) -> tuple[UnilogSemanticAttributeCandidate, ...]:
        retained: dict[tuple[str, str, str | None], UnilogSemanticAttributeCandidate] = {}
        by_name: dict[str, set[tuple[str, str | None]]] = {}
        for item in candidates:
            retained.setdefault((item.semantic_name, item.normalized_value, item.uom), item)
            by_name.setdefault(item.semantic_name, set()).add((item.normalized_value, item.uom))
        return tuple(
            UnilogSemanticAttributeCandidate(
                semantic_name=item.semantic_name,
                raw_value=item.raw_value,
                normalized_value=item.normalized_value,
                uom=item.uom,
                evidence_span=item.evidence_span,
                fact_id=item.fact_id,
                official_label=item.official_label,
                confidence_bp=item.confidence_bp,
                review_required=len(by_name[item.semantic_name]) > 1,
            )
            for item in retained.values()
        )
