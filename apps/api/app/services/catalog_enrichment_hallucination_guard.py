"""Deterministic high-risk claim guards for generated commerce content."""

import re

from app.domain.catalog_enrichment import (
    ClaimRiskCode,
    GroundedGeneratedText,
    TrustedCatalogFact,
    TrustedCatalogFacts,
)
from app.services.catalog_enrichment_response_parser import ParsedCatalogEnrichment

_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?%?", re.IGNORECASE)
_SPEC_CODE = re.compile(r"\b(?:ip|ie)\s*\d{1,3}[a-z]?\b", re.IGNORECASE)
_NUMBER_WORDS = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
}
_UNITS = re.compile(
    r"\b(?:kw|mw|w|hp|v|kv|a|ma|hz|khz|rpm|nm|mm|cm|m|kg|g|bar|psi|°c|phase)\b",
    re.IGNORECASE,
)
_CERTIFICATION = re.compile(r"\b(?:CE|UL|CSA|BIS|ISO|ATEX|RoHS|REACH|IE[234])\b", re.IGNORECASE)
_RISK_PHRASES: tuple[tuple[ClaimRiskCode, tuple[str, ...]], ...] = (
    (
        ClaimRiskCode.UNSUPPORTED_CERTIFICATION_CLAIM,
        ("iec certified", "certified compliant"),
    ),
    (ClaimRiskCode.UNSUPPORTED_WARRANTY_CLAIM, ("warranty", "guarantee")),
    (
        ClaimRiskCode.UNSUPPORTED_MATERIAL_CLAIM,
        ("stainless steel", "cast iron", "aluminium", "aluminum", "copper winding"),
    ),
    (
        ClaimRiskCode.UNSUPPORTED_PERFORMANCE_CLAIM,
        (
            "high efficiency",
            "energy saving",
            "low noise",
            "high torque",
            "maintenance free",
            "corrosion resistant",
            "heavy duty",
            "long life",
            "premium",
            "best",
            "highly durable",
            "energy efficient",
        ),
    ),
    (
        ClaimRiskCode.UNSUPPORTED_USE_CASE_CLAIM,
        (
            "chemical plant",
            "food processing",
            "oil and gas",
            "oil & gas",
            "mining",
            "hvac",
            "water treatment",
            "hazardous area",
        ),
    ),
)


class CatalogEnrichmentHallucinationGuard:
    def inspect(
        self,
        content: ParsedCatalogEnrichment,
        facts: TrustedCatalogFacts,
    ) -> tuple[ClaimRiskCode, ...]:
        fact_map = {fact.fact_id: fact for fact in facts.facts}
        issues: list[ClaimRiskCode] = []
        for item in content.all_items():
            referenced = tuple(
                fact_map[fact_id] for fact_id in item.fact_ids if fact_id in fact_map
            )
            if self._unsupported_numeric(item, referenced):
                issues.append(ClaimRiskCode.UNSUPPORTED_NUMERIC_CLAIM)
            if self._unsupported_unit(item, referenced):
                issues.append(ClaimRiskCode.UNSUPPORTED_UNIT_CLAIM)
            attribute_support = self._normalized(
                " ".join(
                    self._support_text(fact)
                    for fact in referenced
                    if fact.fact_id.startswith("ATTRIBUTE:")
                )
            )
            lowered = self._normalized(item.text)
            if any(
                match.group(0).casefold() not in attribute_support
                for match in _CERTIFICATION.finditer(item.text)
            ):
                issues.append(ClaimRiskCode.UNSUPPORTED_CERTIFICATION_CLAIM)
            for code, phrases in _RISK_PHRASES:
                if any(phrase in lowered and phrase not in attribute_support for phrase in phrases):
                    issues.append(code)
        return tuple(dict.fromkeys(issues))

    def _unsupported_numeric(
        self,
        item: GroundedGeneratedText,
        referenced: tuple[TrustedCatalogFact, ...],
    ) -> bool:
        claims = self._numeric_tokens(item.text)
        supported = {
            token
            for fact in referenced
            if fact.fact_id != "IDENTITY:description"
            for token in self._numeric_tokens(self._support_text(fact))
        }
        return not claims.issubset(supported)

    def _unsupported_unit(
        self,
        item: GroundedGeneratedText,
        referenced: tuple[TrustedCatalogFact, ...],
    ) -> bool:
        claims = {match.group(0).casefold() for match in _UNITS.finditer(item.text)}
        supported = {
            match.group(0).casefold()
            for fact in referenced
            if fact.fact_id != "IDENTITY:description"
            for match in _UNITS.finditer(self._support_text(fact))
        }
        return not claims.issubset(supported)

    @staticmethod
    def _support_text(fact: TrustedCatalogFact) -> str:
        return " ".join(part for part in (fact.display_name, fact.value, fact.unit) if part)

    @staticmethod
    def _numeric_tokens(text: str) -> set[str]:
        tokens = {match.group(0).casefold() for match in _NUMBER.finditer(text)}
        tokens.update(
            re.sub(r"\s+", "", match.group(0).casefold()) for match in _SPEC_CODE.finditer(text)
        )
        lowered = text.casefold()
        tokens.update(
            digit for word, digit in _NUMBER_WORDS.items() if re.search(rf"\b{word}\b", lowered)
        )
        return tokens

    @staticmethod
    def _normalized(text: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"[-_]", " ", text.casefold())).strip()
