"""Manufacturer parsing and evidence-only resolution."""

import re

from app.domain.unilog_challenge import (
    BrandEvidence,
    ManufacturerParseStatus,
    ManufacturerResolution,
    ParsedManufacturer,
    ResolutionStatus,
    UnilogChallengeInputRow,
)
from app.services.unilog_challenge.cleansing import clean_challenge_value

_FINAL_REFERENCE = re.compile(r"^(?P<name>.+?)\s*\((?P<code>[^()]*)\)\s*$")


def parse_part_manufacturer(raw: str | None) -> ParsedManufacturer:
    cleaned = clean_challenge_value(raw)
    if cleaned is None:
        return ParsedManufacturer(
            raw=raw,
            manufacturer_text=None,
            source_reference_code=None,
            status=ManufacturerParseStatus.MISSING,
        )
    match = _FINAL_REFERENCE.fullmatch(cleaned)
    if match:
        name = match.group("name").strip()
        code = match.group("code").strip()
        if name and code:
            return ParsedManufacturer(
                raw=raw,
                manufacturer_text=name,
                source_reference_code=code,
                status=ManufacturerParseStatus.PARSED,
            )
        return ParsedManufacturer(
            raw=raw,
            manufacturer_text=cleaned,
            source_reference_code=None,
            status=ManufacturerParseStatus.AMBIGUOUS,
        )
    return ParsedManufacturer(
        raw=raw,
        manufacturer_text=cleaned,
        source_reference_code=None,
        status=(
            ManufacturerParseStatus.AMBIGUOUS
            if cleaned.endswith(")") or cleaned.startswith("(")
            else ManufacturerParseStatus.UNPARSED
        ),
    )


class EvidenceOnlyManufacturerResolver:
    """Expose supplied evidence without claiming unsupported canonicalization."""

    def resolve(
        self, row: UnilogChallengeInputRow, brand_evidence: BrandEvidence
    ) -> ManufacturerResolution:
        manufacturer = row.parsed_manufacturer
        brands = brand_evidence.candidate_brand_strings
        if manufacturer is None and not brands:
            return ManufacturerResolution(
                raw_manufacturer=row.part_manuf_raw,
                candidate_manufacturer=None,
                candidate_brand=None,
                evidence=(),
                confidence_bp=0,
                review_required=True,
                status=ResolutionStatus.MISSING,
            )
        evidence = tuple(
            item
            for item in (
                f"Part_Manuf:{manufacturer}" if manufacturer else None,
                *(f"BrandField:{brand}" for brand in brands),
            )
            if item is not None
        )
        return ManufacturerResolution(
            raw_manufacturer=row.part_manuf_raw,
            candidate_manufacturer=manufacturer,
            candidate_brand=brands[0] if len(brands) == 1 else None,
            evidence=evidence,
            confidence_bp=7_000 if manufacturer else 4_000,
            review_required=True,
            status=(ResolutionStatus.AMBIGUOUS if len(brands) > 1 else ResolutionStatus.PARTIAL),
        )
