"""Resolve only corroborated organizer brand evidence; placeholders were already cleansed."""

import re

from app.domain.unilog_challenge import (
    ObservedVocabulary,
    ResolutionStatus,
    UnilogBrandResolution,
    UnilogChallengeInputRow,
)
from app.services.unilog_challenge.brand_evidence import extract_brand_evidence


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class UnilogChallengeBrandResolver:
    def resolve(
        self, row: UnilogChallengeInputRow, vocabulary: ObservedVocabulary | None = None
    ) -> UnilogBrandResolution:
        evidence = extract_brand_evidence(row)
        grouped: dict[str, list[str]] = {}
        for value in evidence.candidate_brand_strings:
            grouped.setdefault(_key(value), []).append(value)
        if len(grouped) == 1:
            values = next(iter(grouped.values()))
            corroborated = len(values) > 1 or _key(values[0]) in _key(row.part_desc)
            return UnilogBrandResolution(
                value=values[0],
                status=ResolutionStatus.RESOLVED,
                evidence=tuple(f"organizer-brand:{value}" for value in values),
                confidence_bp=9_500 if corroborated else 8_500,
                review_required=False,
            )
        if len(grouped) > 1:
            return UnilogBrandResolution(
                value=None,
                status=ResolutionStatus.AMBIGUOUS,
                evidence=tuple(
                    f"organizer-brand:{value}" for value in evidence.candidate_brand_strings
                ),
                confidence_bp=0,
                review_required=True,
            )
        observed = (
            ()
            if vocabulary is None
            else tuple(
                brand for brand in sorted(vocabulary.brands) if _key(brand) in _key(row.part_desc)
            )
        )
        if len(observed) == 1:
            return UnilogBrandResolution(
                value=observed[0],
                status=ResolutionStatus.PARTIAL,
                evidence=(f"description-observed-brand:{observed[0]}",),
                confidence_bp=7_000,
                review_required=True,
            )
        return UnilogBrandResolution(
            value=None,
            status=ResolutionStatus.NOT_FOUND,
            evidence=(),
            confidence_bp=0,
            review_required=bool(observed),
        )
