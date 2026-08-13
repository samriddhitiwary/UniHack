"""Deterministic candidate-by-candidate attribute and unit normalization."""

import re
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import AttributeNormalizationCandidateLimitExceededError
from app.domain.attribute_extraction import AttributeCandidate, StructuredAttributeExtractionResult
from app.domain.attribute_normalization import (
    AttributeNormalizationResult,
    NormalizationStatus,
    NormalizedAttributeCandidate,
)
from app.domain.category_schemas import (
    AttributeDataType,
    AttributeDefinition,
    CategoryAttributeSchema,
)
from app.services.numeric_normalizer import NumericNormalizer
from app.services.unit_normalizer import UnitNormalizer


class AttributeNormalizationEngine:
    def __init__(
        self,
        *,
        max_decimal_places: int = 6,
        max_candidates: int = 5_000,
        max_normalized_value_characters: int = 10_000,
    ) -> None:
        if min(max_candidates, max_normalized_value_characters) < 1:
            raise ValueError("normalization limits must be positive")
        self._numeric = NumericNormalizer(max_decimal_places=max_decimal_places)
        self._units = UnitNormalizer()
        self._max_candidates = max_candidates
        self._max_value = max_normalized_value_characters

    def normalize(
        self,
        *,
        job_id: UUID,
        extraction_result: StructuredAttributeExtractionResult,
        schema: CategoryAttributeSchema,
        now: datetime | None = None,
    ) -> AttributeNormalizationResult:
        if len(extraction_result.candidates) > self._max_candidates:
            raise AttributeNormalizationCandidateLimitExceededError()
        timestamp = now or datetime.now(UTC)
        definitions = {item.canonical_name: item for item in schema.attributes}
        candidates = tuple(
            self._normalize_candidate(
                index=index,
                source=source,
                attribute=definitions[source.attribute_name],
                extraction=extraction_result,
                now=timestamp,
            )
            for index, source in enumerate(extraction_result.candidates, 1)
        )
        if any(
            item.normalized_value is not None and len(item.normalized_value) > self._max_value
            for item in candidates
        ):
            raise AttributeNormalizationCandidateLimitExceededError()
        return AttributeNormalizationResult.create(
            job_id=job_id,
            product_id=extraction_result.product_id,
            extraction_id=extraction_result.extraction_id,
            classification_id=extraction_result.classification_id,
            category=extraction_result.category,
            schema_version=extraction_result.schema_version,
            schema_fingerprint=extraction_result.schema_fingerprint,
            candidates=candidates,
            now=timestamp,
        )

    def _normalize_candidate(
        self,
        *,
        index: int,
        source: AttributeCandidate,
        attribute: AttributeDefinition,
        extraction: StructuredAttributeExtractionResult,
        now: datetime,
    ) -> NormalizedAttributeCandidate:
        normalized_value: str | None
        normalized_unit: str | None = None
        conversion_applied = False
        unit_canonicalization_applied = False
        conversion_rule: str | None = None
        confidence = 10_000
        if source.raw_value is None:
            normalized_value, status, confidence = None, NormalizationStatus.INVALID_VALUE, 0
        elif attribute.data_type in {AttributeDataType.NUMBER, AttributeDataType.INTEGER}:
            parsed = self._numeric.parse(source.raw_value)
            if parsed is None or (
                attribute.data_type is AttributeDataType.INTEGER
                and parsed != parsed.to_integral_value()
            ):
                normalized_value, status, confidence = None, NormalizationStatus.INVALID_VALUE, 0
            elif attribute.allowed_units and source.raw_unit is None:
                normalized_value = self._numeric.canonical(parsed)
                status, confidence = NormalizationStatus.UNIT_MISSING, 5_000
            elif attribute.allowed_units:
                unit = self._units.normalize(
                    attribute=attribute, value=parsed, raw_unit=source.raw_unit or ""
                )
                if unit is None:
                    normalized_value, status, confidence = (
                        None,
                        NormalizationStatus.UNSUPPORTED_UNIT,
                        0,
                    )
                else:
                    converted = self._numeric.round_conversion(unit.value)
                    if (
                        attribute.data_type is AttributeDataType.INTEGER
                        and converted != converted.to_integral_value()
                    ):
                        normalized_value, status, confidence = (
                            None,
                            NormalizationStatus.INVALID_VALUE,
                            0,
                        )
                    else:
                        normalized_value = self._numeric.canonical(converted)
                        normalized_unit = unit.normalized_unit
                        conversion_applied = unit.conversion_applied
                        unit_canonicalization_applied = unit.unit_canonicalization_applied
                        conversion_rule = unit.conversion_rule
                        status = (
                            NormalizationStatus.NORMALIZED_WITH_CONVERSION
                            if conversion_applied
                            else NormalizationStatus.NORMALIZED
                        )
            else:
                normalized_value = self._numeric.canonical(parsed)
                status = NormalizationStatus.NORMALIZED
        elif attribute.data_type is AttributeDataType.BOOLEAN:
            token = " ".join(source.raw_value.casefold().split())
            if token in {"true", "yes", "y", "1"}:
                normalized_value, status = "true", NormalizationStatus.NORMALIZED
            elif token in {"false", "no", "n", "0"}:
                normalized_value, status = "false", NormalizationStatus.NORMALIZED
            else:
                normalized_value, status, confidence = None, NormalizationStatus.INVALID_VALUE, 0
        elif attribute.data_type is AttributeDataType.ENUM:
            value = self._text(source.raw_value)
            allowed = {
                self._text(item).casefold(): item
                for item in attribute.validation_rules.allowed_values
            }
            if value.casefold() in allowed:
                normalized_value, status = allowed[value.casefold()], NormalizationStatus.NORMALIZED
            else:
                normalized_value, status, confidence = (
                    value,
                    NormalizationStatus.RAW_TEXT_PRESERVED,
                    7_000,
                )
        else:
            normalized_value = self._canonical_text(attribute.canonical_name, source.raw_value)
            status = NormalizationStatus.NORMALIZED
        return NormalizedAttributeCandidate(
            normalized_candidate_id=f"normalized-candidate-{index:06d}",
            source_candidate_id=source.candidate_id,
            source_extraction_id=extraction.extraction_id,
            classification_id=extraction.classification_id,
            category=extraction.category,
            schema_version=extraction.schema_version,
            schema_fingerprint=extraction.schema_fingerprint,
            attribute_name=source.attribute_name,
            attribute_display_name=source.attribute_display_name,
            data_type=source.attribute_data_type,
            raw_value=source.raw_value,
            raw_unit=source.raw_unit,
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
            normalization_status=status,
            conversion_applied=conversion_applied,
            unit_canonicalization_applied=unit_canonicalization_applied,
            conversion_rule=conversion_rule,
            source_id=source.source_id,
            evidence_type=source.evidence_type,
            evidence_location=source.location,
            evidence_excerpt=source.excerpt,
            extraction_confidence_bp=source.confidence_bp,
            normalization_confidence_bp=confidence,
            created_at=now,
        )

    @staticmethod
    def _text(value: str) -> str:
        return "\n".join(
            " ".join(line.split())
            for line in value.replace("\r\n", "\n").replace("\r", "\n").strip().split("\n")
        )

    @classmethod
    def _canonical_text(cls, attribute_name: str, value: str) -> str:
        normalized = cls._text(value)
        if attribute_name == "ipRating" and re.fullmatch(r"(?i)ip\s*\d{2}[a-z]?", normalized):
            return normalized.replace(" ", "").upper()
        if attribute_name == "insulationClass":
            match = re.fullmatch(r"(?i)(?:class\s*)?([a-z])", normalized)
            if match:
                return match.group(1).upper()
        if attribute_name == "duty" and re.fullmatch(r"(?i)s\d+", normalized):
            return normalized.upper()
        return normalized
