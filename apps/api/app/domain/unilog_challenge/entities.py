"""Immutable domain models for challenge inputs, labels, and evidence."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from types import MappingProxyType

from app.domain.unilog_challenge.delivery_schema import (
    UNILOG_DELIVERY_HEADER_SET,
    UNILOG_DELIVERY_HEADERS,
)
from app.domain.unilog_challenge.enums import (
    AlignmentStatus,
    ComparisonStatus,
    DatasetSplit,
    EvidenceSourceType,
    EvidenceStrength,
    ManufacturerParseStatus,
    ResolutionStatus,
)

DeliveryValue = str | int | Decimal | None


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DatasetMetadata:
    filename: str
    sha256: str
    row_count: int
    column_count: int
    parser_version: str
    imported_at: datetime

    def __post_init__(self) -> None:
        if not self.filename or len(self.sha256) != 64:
            raise ValueError("dataset identity is invalid")
        if self.row_count < 0 or self.column_count < 1:
            raise ValueError("dataset dimensions are invalid")
        if not self.parser_version:
            raise ValueError("parser version is required")
        object.__setattr__(self, "imported_at", _utc(self.imported_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class ParsedManufacturer:
    raw: str | None
    manufacturer_text: str | None
    source_reference_code: str | None
    status: ManufacturerParseStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class BrandEvidence:
    e1_raw: str | None
    unilog_raw: str | None
    dib_raw: str | None
    e1_clean: str | None
    unilog_clean: str | None
    dib_clean: str | None
    candidate_brand_strings: tuple[str, ...]
    description_text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogChallengeInputRow:
    row_id: str
    source_row_number: int
    mfg_part_num: str
    part_desc: str
    e1_brand_raw: str
    unilog_brand_raw: str
    dib_brand_raw: str
    part_manuf_raw: str
    e1_brand_clean: str | None
    unilog_brand_clean: str | None
    dib_brand_clean: str | None
    parsed_manufacturer: str | None
    source_reference_code: str | None
    manufacturer_parse_status: ManufacturerParseStatus

    def __post_init__(self) -> None:
        if len(self.row_id) != 64 or self.source_row_number < 2:
            raise ValueError("challenge row identity is invalid")
        if not self.mfg_part_num or not self.part_desc:
            raise ValueError("part number and description are required")


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldProvenance:
    field_name: str
    value: DeliveryValue
    source_type: EvidenceSourceType
    source_reference: str
    method: str
    evidence_strength: EvidenceStrength
    confidence_bp: int
    review_required: bool

    def __post_init__(self) -> None:
        if self.field_name not in UNILOG_DELIVERY_HEADER_SET:
            raise ValueError("provenance field is not in the delivery schema")
        if not 0 <= self.confidence_bp <= 10_000:
            raise ValueError("confidence_bp must be between 0 and 10000")
        if not self.source_reference or not self.method:
            raise ValueError("provenance source and method are required")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogDeliveryRecord:
    _values: Mapping[str, DeliveryValue]

    def __post_init__(self) -> None:
        keys = tuple(self._values)
        if keys != UNILOG_DELIVERY_HEADERS:
            raise ValueError("delivery record keys must match the exact ordered schema")
        object.__setattr__(self, "_values", MappingProxyType(dict(self._values)))

    @classmethod
    def blank(cls) -> "UnilogDeliveryRecord":
        return cls(_values={header: None for header in UNILOG_DELIVERY_HEADERS})

    @classmethod
    def from_mapping(cls, values: Mapping[str, DeliveryValue]) -> "UnilogDeliveryRecord":
        return cls(_values=values)

    def as_dict(self) -> dict[str, DeliveryValue]:
        return dict(self._values)

    def value(self, header: str) -> DeliveryValue:
        if header not in UNILOG_DELIVERY_HEADER_SET:
            raise KeyError(header)
        return self._values[header]


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogGroundTruthRecord:
    source_output_row_number: int
    mfg_part_num: str
    expected: UnilogDeliveryRecord
    populated_fields: frozenset[str]
    split: DatasetSplit
    input_row_id: str | None = None

    def __post_init__(self) -> None:
        if self.source_output_row_number < 2 or not self.mfg_part_num:
            raise ValueError("ground-truth identity is invalid")
        actual = frozenset(
            key
            for key, value in self.expected.as_dict().items()
            if value is not None and str(value) != ""
        )
        if self.populated_fields != actual:
            raise ValueError("ground-truth populated-field mask is inconsistent")


@dataclass(frozen=True, slots=True, kw_only=True)
class GroundTruthAlignment:
    status: AlignmentStatus
    mfg_part_num: str
    output_row_number: int
    candidate_row_ids: tuple[str, ...]
    aligned_input_row_id: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldComparison:
    field_name: str
    expected_value: DeliveryValue
    actual_value: DeliveryValue
    status: ComparisonStatus
    normalization_method: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ManufacturerResolution:
    raw_manufacturer: str | None
    candidate_manufacturer: str | None
    candidate_brand: str | None
    evidence: tuple[str, ...]
    confidence_bp: int
    review_required: bool
    status: ResolutionStatus

    def __post_init__(self) -> None:
        if not 0 <= self.confidence_bp <= 10_000:
            raise ValueError("confidence_bp must be between 0 and 10000")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeCandidate:
    label: str
    raw_value: str
    normalized_value: str | None
    uom: str | None
    source: EvidenceSourceType
    confidence_bp: int
    review_required: bool

    def __post_init__(self) -> None:
        if not self.label or not self.raw_value:
            raise ValueError("attribute label and raw value are required")
        if not 0 <= self.confidence_bp <= 10_000:
            raise ValueError("confidence_bp must be between 0 and 10000")


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReferences:
    manufacturer_url: str | None
    reference_urls: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.reference_urls) > 5:
            raise ValueError("at most five reference URLs are supported")


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedVocabulary:
    manufacturers: frozenset[str]
    brands: frozenset[str]
    classpaths: frozenset[str]
    attribute_labels: frozenset[str]
    uoms: frozenset[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportStatistics:
    input_rows: int
    expected_output_rows: int
    input_columns: int
    expected_output_columns: int
    aligned_rows: int
    unaligned_rows: int
    ambiguous_rows: int
    duplicate_input_keys: int
    placeholder_values: int
    manufacturer_parse_successes: int
    manufacturer_parse_ambiguous: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogChallengeImport:
    import_id: str
    input_metadata: DatasetMetadata
    output_metadata: DatasetMetadata
    input_rows: tuple[UnilogChallengeInputRow, ...]
    ground_truth_rows: tuple[UnilogGroundTruthRecord, ...]
    alignments: tuple[GroundTruthAlignment, ...]
    observed_vocabulary: ObservedVocabulary
    statistics: ImportStatistics

    def __post_init__(self) -> None:
        if len(self.import_id) != 64:
            raise ValueError("import identity is invalid")
