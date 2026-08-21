"""Future-facing enrichment interfaces with no network implementation."""

from typing import Protocol

from app.domain.unilog_challenge.entities import (
    BrandEvidence,
    ManufacturerResolution,
    UnilogAttributeCandidate,
    UnilogChallengeInputRow,
)


class ManufacturerResolver(Protocol):
    def resolve(
        self, row: UnilogChallengeInputRow, brand_evidence: BrandEvidence
    ) -> ManufacturerResolution: ...


class BrandResolver(Protocol):
    def resolve(self, evidence: BrandEvidence) -> ManufacturerResolution: ...


class UnilogProductClassifier(Protocol):
    def classify(self, row: UnilogChallengeInputRow) -> tuple[str | None, int, bool]: ...


class UnilogAttributeEnricher(Protocol):
    def enrich(self, row: UnilogChallengeInputRow) -> tuple[UnilogAttributeCandidate, ...]: ...


class ManufacturerEvidenceProvider(Protocol):
    def retrieve(self, manufacturer: str, part_number: str) -> tuple[str, ...]: ...


class UnilogDescriptionBuilder(Protocol):
    def build(
        self, row: UnilogChallengeInputRow, attributes: tuple[UnilogAttributeCandidate, ...]
    ) -> dict[str, str | None]: ...
