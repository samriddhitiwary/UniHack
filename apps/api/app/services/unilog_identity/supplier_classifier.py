"""Dataset-observed supplier-likeness and manufacturer-role evidence."""

import re

from app.domain.unilog_challenge import UnilogChallengeInputRow
from app.domain.unilog_identity import IdentityEvidenceSource, UnilogOrganizationEvidence
from app.services.unilog_challenge.manufacturer import parse_part_manufacturer

_SUPPLIER_PATTERN = re.compile(
    r"\b(?:industrial\s+supply|supply|supplies|distribution|distributor|wholesale|"
    r"sales|dealer|dealers|cooperative|building\s+materials|lumber)\b",
    re.IGNORECASE,
)
_MANUFACTURER_PATTERN = re.compile(
    r"\b(?:manufacturing|manufacturer|mfg|products?|tools?|machinery|industries|"
    r"corp|company|lighting|electric|abrasives|wire|brands|systems)\b",
    re.IGNORECASE,
)


class SupplierEvidenceClassifier:
    def classify(
        self, raw_value: str, *, support_count: int = 1, example_rows: tuple[str, ...] = ()
    ) -> UnilogOrganizationEvidence | None:
        parsed = parse_part_manufacturer(raw_value)
        name = parsed.manufacturer_text
        if name is None or name.strip(" -") == "":
            return None
        supplier_terms = tuple(
            match.group().casefold() for match in _SUPPLIER_PATTERN.finditer(name)
        )
        manufacturer_terms = tuple(
            match.group().casefold() for match in _MANUFACTURER_PATTERN.finditer(name)
        )
        supplier = 9_000 if supplier_terms else 2_000
        manufacturer = (
            1_500
            if supplier_terms
            else 8_500
            if manufacturer_terms and support_count >= 2
            else 6_500
            if support_count >= 2
            else 4_500
        )
        reasons = tuple(
            [
                *(f"SUPPLIER_TOKEN:{item}" for item in supplier_terms),
                *(f"MANUFACTURER_TOKEN:{item}" for item in manufacturer_terms),
                f"DATASET_SUPPORT:{support_count}",
            ]
        )
        return UnilogOrganizationEvidence(
            raw_value=raw_value,
            clean_value=raw_value.strip(),
            parsed_name=name,
            source_reference_code=parsed.source_reference_code,
            source_field=IdentityEvidenceSource.PART_MANUF,
            supplier_likelihood_bp=supplier,
            manufacturer_likelihood_bp=manufacturer,
            evidence_reasons=reasons,
            support_count=support_count,
            example_rows=example_rows,
        )

    def classify_row(self, row: UnilogChallengeInputRow) -> UnilogOrganizationEvidence | None:
        return self.classify(row.part_manuf_raw, example_rows=(row.row_id,))
