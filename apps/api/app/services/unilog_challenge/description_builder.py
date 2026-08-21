"""Deterministic descriptions that transform trusted facts without adding claims."""

import re
from collections.abc import Mapping

from app.domain.unilog_challenge import (
    EvidenceSourceType,
    EvidenceStrength,
    FieldProvenance,
    UnilogDescriptionResult,
)

_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[-/.]\d+)*(?![A-Za-z])")
_FORBIDDEN_UNGROUNDED = re.compile(
    r"\b(?:best|industry-leading|premium|high-performance|durable|professional-grade)\b",
    re.I,
)


class UnilogDescriptionBuilder:
    def build_all(
        self, facts: Mapping[str, str], *, raw_evidence: str
    ) -> tuple[UnilogDescriptionResult, ...]:
        product_type = facts.get("product_type")
        if product_type is None:
            return tuple(self._blank(field) for field in self._fields())
        brand = facts.get("brand")
        manufacturer = facts.get("manufacturer")
        mpn = facts.get("mpn")
        series = facts.get("series")
        key_values = [
            facts[key] for key in ("dimensions", "material", "grit", "quantity") if key in facts
        ]
        product_name = product_type
        invoice_parts = [product_type, *key_values]
        invoice = self._bounded_invoice(invoice_parts)
        mobile = ", ".join(self._unique_parts([manufacturer, brand, product_type, series, mpn]))
        short = " ".join(self._unique_parts([brand, series, mpn, product_type, *key_values]))
        retail = ", ".join(self._unique_parts([series, product_type, *key_values]))
        long = self._factual_sentence(
            self._unique_parts([brand, product_type, series, mpn, *key_values])
        )
        marketing = self._factual_sentence(
            self._unique_parts([brand, product_type, mpn, *key_values])
        )
        candidates = {
            "Product Name": product_name,
            "INVOICE_DESC": invoice,
            "MOBILE_DESC": mobile,
            "SHORT_DESC": short,
            "LONG_DESC1": long,
            "RETAIL_DESC": retail,
            "MARKETING_DESCRIPTION": marketing,
        }
        return tuple(
            self._result(field, value, facts, raw_evidence=raw_evidence)
            for field, value in candidates.items()
        )

    @staticmethod
    def _fields() -> tuple[str, ...]:
        return (
            "Product Name",
            "INVOICE_DESC",
            "MOBILE_DESC",
            "SHORT_DESC",
            "LONG_DESC1",
            "RETAIL_DESC",
            "MARKETING_DESCRIPTION",
        )

    @staticmethod
    def _unique_parts(parts: list[str | None]) -> list[str]:
        retained: list[str] = []
        seen: set[str] = set()
        for part in parts:
            if part is None:
                continue
            key = re.sub(r"\s+", " ", part).strip().casefold()
            if key and key not in seen:
                retained.append(part.strip())
                seen.add(key)
        return retained

    @staticmethod
    def _bounded_invoice(parts: list[str]) -> str:
        retained: list[str] = []
        for part in parts:
            candidate = " ".join((*retained, part)).upper()
            if len(candidate) <= 40:
                retained.append(part)
        return " ".join(retained).upper()

    @staticmethod
    def _factual_sentence(parts: list[str]) -> str:
        return f"{', '.join(parts)}." if parts else ""

    def _result(
        self,
        field: str,
        value: str,
        facts: Mapping[str, str],
        *,
        raw_evidence: str,
    ) -> UnilogDescriptionResult:
        issues = list(self._validate(field, value, facts, raw_evidence))
        fatal = any(issue.startswith("INVALID_") for issue in issues)
        safe_value = None if fatal or not value else value
        fact_ids = (
            ()
            if safe_value is None
            else tuple(
                f"FACT:{key}"
                for key, fact_value in facts.items()
                if fact_value.casefold() in safe_value.casefold()
            )
        )
        provenance = (
            ()
            if safe_value is None
            else (
                FieldProvenance(
                    field_name=field,
                    value=safe_value,
                    source_type=EvidenceSourceType.DETERMINISTIC_PARSE,
                    source_reference=",".join(fact_ids),
                    method="grounded-unilog-description-builder-v1",
                    evidence_strength=EvidenceStrength.DERIVED,
                    confidence_bp=9_000,
                    review_required=bool(issues),
                ),
            )
        )
        return UnilogDescriptionResult(
            field_name=field,
            value=safe_value,
            fact_ids=fact_ids,
            field_provenance=provenance,
            confidence_bp=9_000 if safe_value else 0,
            validation_issues=tuple(issues),
        )

    @staticmethod
    def _validate(
        field: str, value: str, facts: Mapping[str, str], raw_evidence: str
    ) -> tuple[str, ...]:
        issues: list[str] = []
        if field == "INVOICE_DESC" and (len(value) > 40 or value != value.upper()):
            issues.append("INVALID_INVOICE_FORMAT")
        if field == "MOBILE_DESC" and not 60 <= len(value) <= 80:
            issues.append("FORMAT_WARNING_MOBILE_LENGTH")
        support = " ".join((raw_evidence, *facts.values()))
        supported_numbers = set(_NUMBER.findall(support))
        if not set(_NUMBER.findall(value)).issubset(supported_numbers):
            issues.append("INVALID_UNSUPPORTED_NUMBER")
        if _FORBIDDEN_UNGROUNDED.search(value):
            issues.append("INVALID_UNSUPPORTED_MARKETING_CLAIM")
        return tuple(issues)

    @staticmethod
    def _blank(field: str) -> UnilogDescriptionResult:
        return UnilogDescriptionResult(
            field_name=field,
            value=None,
            fact_ids=(),
            field_provenance=(),
            confidence_bp=0,
            validation_issues=("MISSING_PRODUCT_TYPE",),
        )
