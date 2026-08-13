"""Deterministic schema-aware raw candidate extraction without normalization."""

import re
from dataclasses import replace
from datetime import UTC, datetime

from app.core.exceptions import StructuredAttributeExtractionLimitExceededError
from app.domain.attribute_extraction import (
    AttributeCandidate,
    AttributeExtractionEvidence,
    AttributeMatchType,
    AttributeValueParseStatus,
)
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    CategoryAttributeSchema,
)
from app.domain.category_schemas.validation import normalize_alias

_NUMBER = re.compile(r"^([+-]?\d+(?:\.\d+)?)(?:\s*(\S.*))?$")


class StructuredAttributeExtractionEngine:
    def __init__(
        self,
        *,
        max_candidates: int = 5_000,
        max_candidates_per_attribute: int = 100,
        max_excerpt_characters: int = 1_000,
    ) -> None:
        if min(max_candidates, max_candidates_per_attribute, max_excerpt_characters) < 1:
            raise ValueError("candidate limits must be positive")
        self._max_candidates = max_candidates
        self._max_per_attribute = max_candidates_per_attribute
        self._max_excerpt = max_excerpt_characters

    def extract(
        self,
        *,
        schema: CategoryAttributeSchema,
        evidence: tuple[AttributeExtractionEvidence, ...],
        now: datetime | None = None,
    ) -> tuple[tuple[AttributeCandidate, ...], tuple[str, ...], int]:
        timestamp = now or datetime.now(UTC)
        found: list[tuple[int, AttributeCandidate]] = []
        warnings: list[str] = []
        seen: set[tuple[str, str | None, str | None, object, str]] = set()
        duplicates = 0
        counts: dict[str, int] = {}
        for item in evidence:
            matched = self._match(schema, item)
            if matched is None:
                continue
            attribute, label, raw, match_type = matched
            raw_value, raw_unit, parse_status, parse_quality = self._parse(attribute, raw)
            if parse_status is AttributeValueParseStatus.MISSING_VALUE:
                self._warning(warnings, "ATTRIBUTE_VALUE_MISSING")
            label_quality = {
                AttributeMatchType.EXACT: 9_000,
                AttributeMatchType.NORMALIZED: 8_000,
                AttributeMatchType.CONTEXTUAL: 8_500,
            }[match_type]
            confidence = label_quality * item.source_quality_bp * parse_quality // 100_000_000
            key = (attribute.canonical_name, raw_value, raw_unit, item.source_id, item.location)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            counts[attribute.canonical_name] = counts.get(attribute.canonical_name, 0) + 1
            if counts[attribute.canonical_name] > self._max_per_attribute:
                raise StructuredAttributeExtractionLimitExceededError()
            candidate = AttributeCandidate(
                candidate_id="candidate-pending",
                attribute_name=attribute.canonical_name,
                attribute_display_name=attribute.display_name,
                attribute_data_type=attribute.data_type,
                raw_value=raw_value,
                raw_unit=raw_unit,
                source_id=item.source_id,
                evidence_id=item.evidence_id,
                evidence_type=item.evidence_type,
                location=item.location,
                excerpt=item.text[: self._max_excerpt],
                matched_label=label,
                match_type=match_type,
                confidence_bp=confidence,
                source_quality_bp=item.source_quality_bp,
                parse_status=parse_status,
                created_at=timestamp,
            )
            found.append((attribute.display_order, candidate))
            if len(found) > self._max_candidates:
                raise StructuredAttributeExtractionLimitExceededError()
        found.sort(
            key=lambda value: (
                value[0],
                -value[1].confidence_bp,
                value[1].source_id.hex,
                value[1].location,
                value[1].raw_value or "",
            )
        )
        candidates = tuple(
            replace(value, candidate_id=f"candidate-{index:06d}")
            for index, (_, value) in enumerate(found, start=1)
        )
        return candidates, tuple(warnings), duplicates

    @staticmethod
    def _warning(warnings: list[str], code: str) -> None:
        if code not in warnings:
            warnings.append(code)

    @staticmethod
    def _match(
        schema: CategoryAttributeSchema, evidence: AttributeExtractionEvidence
    ) -> tuple[AttributeDefinition, str, str | None, AttributeMatchType] | None:
        if evidence.label_hint is not None:
            attribute = schema.resolve_alias(evidence.label_hint)
            if attribute is None:
                return None
            return (
                attribute,
                evidence.label_hint,
                evidence.value_hint,
                AttributeMatchType.CONTEXTUAL,
            )
        text = evidence.text.strip()
        for separator in (":", "=", " - "):
            if separator in text:
                label, raw = text.split(separator, 1)
                result = StructuredAttributeExtractionEngine._resolve(schema, label.strip())
                if result:
                    attribute, match_type = result
                    return attribute, label.strip(), raw.strip() or None, match_type
        aliases: list[tuple[str, AttributeDefinition]] = []
        for attribute in schema.attributes:
            aliases.extend(
                (alias, attribute)
                for alias in (attribute.canonical_name, attribute.display_name, *attribute.aliases)
            )
        for alias, attribute in sorted(aliases, key=lambda item: len(item[0]), reverse=True):
            if text.casefold().startswith(alias.casefold()) and (
                len(text) == len(alias) or text[len(alias)].isspace()
            ):
                raw = text[len(alias) :].strip()
                exact = text[: len(alias)].casefold() == alias.casefold()
                return (
                    attribute,
                    text[: len(alias)],
                    raw or None,
                    (AttributeMatchType.EXACT if exact else AttributeMatchType.NORMALIZED),
                )
        return None

    @staticmethod
    def _resolve(
        schema: CategoryAttributeSchema, label: str
    ) -> tuple[AttributeDefinition, AttributeMatchType] | None:
        attribute = schema.resolve_alias(label)
        if attribute is None:
            return None
        exact = any(
            label.casefold() == value.casefold()
            for value in (attribute.canonical_name, attribute.display_name, *attribute.aliases)
        )
        return attribute, AttributeMatchType.EXACT if exact else AttributeMatchType.NORMALIZED

    @staticmethod
    def _parse(
        attribute: AttributeDefinition, raw: str | None
    ) -> tuple[str | None, str | None, AttributeValueParseStatus, int]:
        if raw is None or not raw.strip():
            return None, None, AttributeValueParseStatus.MISSING_VALUE, 7_000
        value = raw.strip()
        if attribute.data_type in {AttributeDataType.TEXT, AttributeDataType.ENUM}:
            return value, None, AttributeValueParseStatus.RAW_TEXT, 9_000
        if attribute.data_type is AttributeDataType.BOOLEAN:
            if value.casefold() in {"yes", "no", "true", "false"}:
                return value, None, AttributeValueParseStatus.PARSED, 10_000
            return value, None, AttributeValueParseStatus.RAW_TEXT, 7_000
        match = _NUMBER.fullmatch(value)
        if match is None or (
            attribute.data_type is AttributeDataType.INTEGER and "." in match.group(1)
        ):
            return value, None, AttributeValueParseStatus.RAW_TEXT, 7_000
        number, unit = match.groups()
        allowed = {normalize_alias(item.symbol) for item in attribute.allowed_units}
        if unit is not None and normalize_alias(unit) not in allowed:
            return value, None, AttributeValueParseStatus.RAW_TEXT, 7_000
        quality = 10_000 if unit is not None or not attribute.allowed_units else 8_500
        return number, unit, AttributeValueParseStatus.PARSED, quality
