"""Runtime indexed product-type resolution with exact source evidence."""

import re
from collections import defaultdict

from app.domain.unilog_classification import (
    AbbreviationStatus,
    ClassificationReviewReason,
    ProductTypeMatchMethod,
    UnilogClassificationVocabulary,
    UnilogProductTypeResolution,
)
from app.services.unilog_classification.vocabulary_builder import normalize_product_phrase
from app.services.unilog_classification.vocabulary_store import (
    load_default_classification_vocabulary,
)

# Compatibility policy already verified by SPEC-042 before the dataset-derived expansion.
_LEGACY_VERIFIED_PRODUCT_TYPES = (
    "Sanding Belt",
    "Stikit Film",
    "Dishwasher",
    "Coupling",
    "Faucet",
    "Sanding Disc",
    "Abrasive Disc",
    "Drill Bit",
    "Filter",
    "Valve",
    "Pump",
    "Motor",
)


class UnilogProductTypeResolver:
    def __init__(self, vocabulary: UnilogClassificationVocabulary | None = None) -> None:
        self.vocabulary = vocabulary or load_default_classification_vocabulary()
        variants: dict[str, list[tuple[str, str | None, int]]] = defaultdict(list)
        for entry in self.vocabulary.entries:
            for variant in entry.variants:
                variants[normalize_product_phrase(variant)].append(
                    (entry.canonical_product_type, entry.product_family, entry.confidence_bp)
                )
        self._variants = dict(variants)
        self._abbreviations = {
            item.raw_token.casefold()
            for item in self.vocabulary.abbreviations
            if item.status is AbbreviationStatus.VERIFIED_OBSERVED
        }

    def resolve(self, description: str) -> UnilogProductTypeResolution:
        matches: list[tuple[int, int, str, str | None, int, str]] = []
        for normalized, variant_candidates in self._variants.items():
            pattern = (
                r"(?<![a-z0-9])"
                + r"[\s\-_/]*".join(map(re.escape, normalized.split()))
                + r"(?![a-z0-9])"
            )
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                for canonical, family, confidence in variant_candidates:
                    matches.append(
                        (
                            match.end() - match.start(),
                            match.start(),
                            canonical,
                            family,
                            confidence,
                            match.group(),
                        )
                    )
        if not matches:
            legacy = self._legacy_match(description)
            if legacy is not None:
                return legacy
            normalized = normalize_product_phrase(description)
            reason = (
                ClassificationReviewReason.PRODUCT_TYPE_GENERIC
                if normalized
                and set(normalized.split())
                <= {
                    "accessory",
                    "assembly",
                    "component",
                    "item",
                    "kit",
                    "part",
                    "product",
                    "replacement",
                }
                else ClassificationReviewReason.PRODUCT_TYPE_UNKNOWN
            )
            return UnilogProductTypeResolution(
                product_type=None,
                product_family=None,
                match_method=ProductTypeMatchMethod.NOT_FOUND,
                evidence_span=None,
                evidence_text=None,
                confidence_bp=0,
                review_required=True,
                review_reasons=(reason,),
            )
        best_length = max(item[0] for item in matches)
        best = [item for item in matches if item[0] == best_length]
        candidates = tuple(sorted({item[2] for item in best}))
        if len(candidates) != 1:
            return UnilogProductTypeResolution(
                product_type=None,
                product_family=None,
                match_method=ProductTypeMatchMethod.AMBIGUOUS,
                evidence_span=None,
                evidence_text=None,
                confidence_bp=5_000,
                review_required=True,
                review_reasons=(ClassificationReviewReason.PRODUCT_TYPE_AMBIGUOUS,),
                candidate_product_types=candidates,
            )
        selected = min(
            (item for item in best if item[2] == candidates[0]), key=lambda item: item[1]
        )
        start = selected[1]
        evidence = selected[5]
        explicit = normalize_product_phrase(evidence) == normalize_product_phrase(selected[2])
        evidence_tokens = set(normalize_product_phrase(evidence).split())
        method = (
            ProductTypeMatchMethod.EXPLICIT_PHRASE
            if explicit
            else ProductTypeMatchMethod.OBSERVED_ABBREVIATION
            if evidence_tokens & self._abbreviations
            else ProductTypeMatchMethod.OBSERVED_VARIANT
        )
        return UnilogProductTypeResolution(
            product_type=selected[2],
            product_family=selected[3],
            match_method=method,
            evidence_span=(start, start + len(evidence)),
            evidence_text=evidence,
            confidence_bp=selected[4],
            review_required=False,
            review_reasons=(),
            candidate_product_types=candidates,
        )

    @staticmethod
    def _legacy_match(description: str) -> UnilogProductTypeResolution | None:
        lowered = description.casefold()
        matched = tuple(
            value for value in _LEGACY_VERIFIED_PRODUCT_TYPES if value.casefold() in lowered
        )
        if not matched:
            return None
        product_type = max(matched, key=len)
        start = lowered.index(product_type.casefold())
        evidence = description[start : start + len(product_type)]
        return UnilogProductTypeResolution(
            product_type=product_type,
            product_family=None,
            match_method=ProductTypeMatchMethod.DESCRIPTION_PATTERN,
            evidence_span=(start, start + len(evidence)),
            evidence_text=evidence,
            confidence_bp=8_500,
            review_required=False,
            review_reasons=(),
            candidate_product_types=(product_type,),
        )


def resolve_product_type(description: str) -> UnilogProductTypeResolution:
    """Resolve one description through the cached default vocabulary."""

    return UnilogProductTypeResolver().resolve(description)
