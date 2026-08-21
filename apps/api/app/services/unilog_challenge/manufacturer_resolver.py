"""Challenge manufacturer resolver that keeps supplier evidence distinct."""

import re

from app.domain.unilog_challenge import (
    ManufacturerResolution,
    ResolutionStatus,
    UnilogBrandResolution,
    UnilogChallengeInputRow,
)

_SUPPLIER_TERMS = re.compile(
    r"\b(?:dealer|dealers|distribution|distributor|industrial supply|"
    r"cooperative|wholesale|retail)\b",
    re.I,
)


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


class UnilogChallengeManufacturerResolver:
    def resolve(
        self, row: UnilogChallengeInputRow, brand: UnilogBrandResolution
    ) -> ManufacturerResolution:
        candidate = row.parsed_manufacturer
        if candidate is None:
            return ManufacturerResolution(
                raw_manufacturer=row.part_manuf_raw,
                candidate_manufacturer=None,
                candidate_brand=brand.value,
                evidence=brand.evidence,
                confidence_bp=0,
                review_required=True,
                status=ResolutionStatus.MISSING,
            )
        supplier_like = bool(_SUPPLIER_TERMS.search(candidate))
        agrees = brand.value is not None and (
            _key(candidate) in _key(brand.value) or _key(brand.value) in _key(candidate)
        )
        if supplier_like or (brand.value is not None and not agrees):
            return ManufacturerResolution(
                raw_manufacturer=row.part_manuf_raw,
                candidate_manufacturer=None,
                candidate_brand=brand.value,
                evidence=(f"supplier-candidate:{candidate}", *brand.evidence),
                confidence_bp=0,
                review_required=True,
                status=ResolutionStatus.AMBIGUOUS,
            )
        return ManufacturerResolution(
            raw_manufacturer=row.part_manuf_raw,
            candidate_manufacturer=candidate,
            candidate_brand=brand.value,
            evidence=(f"Part_Manuf:{candidate}", *brand.evidence),
            confidence_bp=9_000 if agrees else 7_000,
            review_required=not agrees,
            status=ResolutionStatus.RESOLVED if agrees else ResolutionStatus.PARTIAL,
        )
