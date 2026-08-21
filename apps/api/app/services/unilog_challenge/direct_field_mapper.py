"""Central direct-copy policy for semantically safe challenge fields."""

from app.domain.unilog_challenge import (
    EvidenceSourceType,
    EvidenceStrength,
    FieldPopulationStrategy,
    FieldProvenance,
    FieldValidationStatus,
    UnilogChallengeInputRow,
    UnilogFieldResolution,
)

_DIRECT_FIELDS = (
    ("Mfg_Part_Num", "mfg_part_num"),
    ("Part_Desc", "part_desc"),
    ("E1_Brand", "e1_brand_raw"),
    ("Unilog_Brand", "unilog_brand_raw"),
    ("DIB_Brand", "dib_brand_raw"),
    ("Part_Manuf", "part_manuf_raw"),
    ("MANUFACTURER_PART_NUMBER", "mfg_part_num"),
)


class UnilogDirectFieldMapper:
    def map(self, row: UnilogChallengeInputRow) -> tuple[UnilogFieldResolution, ...]:
        return tuple(
            _resolution(field, str(getattr(row, source)), source)
            for field, source in _DIRECT_FIELDS
        )


def _resolution(field: str, value: str, source: str) -> UnilogFieldResolution:
    provenance = FieldProvenance(
        field_name=field,
        value=value,
        source_type=EvidenceSourceType.RAW_INPUT,
        source_reference=source,
        method="unilog-direct-field-policy-v1",
        evidence_strength=EvidenceStrength.DIRECT,
        confidence_bp=10_000,
        review_required=False,
    )
    return UnilogFieldResolution(
        field_name=field,
        value=value,
        strategy=FieldPopulationStrategy.DIRECT_COPY,
        validation_status=FieldValidationStatus.VALID,
        provenance=provenance,
        confidence_bp=10_000,
        review_required=False,
    )
