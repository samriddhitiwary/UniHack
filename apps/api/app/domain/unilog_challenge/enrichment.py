"""Evidence-grounded challenge enrichment models kept outside the Product aggregate."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from types import MappingProxyType

from app.domain.unilog_challenge.entities import (
    FieldProvenance,
    UnilogChallengeInputRow,
    UnilogDeliveryRecord,
)
from app.domain.unilog_challenge.enums import (
    BatchRowStatus,
    FieldPopulationStrategy,
    FieldValidationStatus,
    ResolutionStatus,
)

UNILOG_ENRICHMENT_POLICY_VERSION = "unilog-enrichment-policy-v1"
MAX_UNILOG_BATCH_ROWS = 1_000


def _confidence(value: int) -> None:
    if isinstance(value, bool) or not 0 <= value <= 10_000:
        raise ValueError("confidence must be between 0 and 10000 basis points")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogEnrichmentRequest:
    input_row_id: str
    policy_version: str = UNILOG_ENRICHMENT_POLICY_VERSION
    provider: str | None = None
    model: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        if len(self.input_row_id) != 64 or not self.policy_version:
            raise ValueError("enrichment request identity is invalid")
        values = (self.provider, self.model, self.model_version)
        if any(value is not None and not value.strip() for value in values):
            raise ValueError("configured model identity values must be nonblank")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogMeasurementCandidate:
    raw_text: str
    numeric_value: Fraction
    raw_unit: str
    normalized_unit: str
    evidence_span: tuple[int, int]
    confidence_bp: int

    def __post_init__(self) -> None:
        if not self.raw_text or self.numeric_value < 0 or not self.normalized_unit:
            raise ValueError("measurement candidate is invalid")
        if self.evidence_span[0] < 0 or self.evidence_span[1] <= self.evidence_span[0]:
            raise ValueError("measurement evidence span is invalid")
        _confidence(self.confidence_bp)

    @property
    def exact_value(self) -> str:
        whole, remainder = divmod(self.numeric_value.numerator, self.numeric_value.denominator)
        if not remainder:
            return str(whole)
        return (
            f"{whole}-{remainder}/{self.numeric_value.denominator}"
            if whole
            else (f"{remainder}/{self.numeric_value.denominator}")
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogSemanticAttributeCandidate:
    semantic_name: str
    raw_value: str
    normalized_value: str
    uom: str | None
    evidence_span: tuple[int, int]
    fact_id: str
    official_label: str | None
    confidence_bp: int
    review_required: bool = False

    def __post_init__(self) -> None:
        if not all((self.semantic_name, self.raw_value, self.normalized_value, self.fact_id)):
            raise ValueError("attribute candidate values are required")
        if self.evidence_span[0] < 0 or self.evidence_span[1] <= self.evidence_span[0]:
            raise ValueError("attribute evidence span is invalid")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogProductClassification:
    product_type_candidate: str | None
    classpath: str | None
    leaf_node: str | None
    confidence_bp: int
    evidence: tuple[str, ...]
    review_required: bool

    def __post_init__(self) -> None:
        _confidence(self.confidence_bp)
        if self.classpath is not None and self.leaf_node is None:
            raise ValueError("known classpath requires a leaf node")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBrandResolution:
    value: str | None
    status: ResolutionStatus
    evidence: tuple[str, ...]
    confidence_bp: int
    review_required: bool

    def __post_init__(self) -> None:
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogDescriptionResult:
    field_name: str
    value: str | None
    fact_ids: tuple[str, ...]
    field_provenance: tuple[FieldProvenance, ...]
    confidence_bp: int
    validation_issues: tuple[str, ...]

    def __post_init__(self) -> None:
        _confidence(self.confidence_bp)
        if self.value is None and self.fact_ids:
            raise ValueError("blank description cannot reference facts")
        if len(set(self.fact_ids)) != len(self.fact_ids):
            raise ValueError("description fact references must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogItemFeature:
    value: str
    fact_ids: tuple[str, ...]
    confidence_bp: int

    def __post_init__(self) -> None:
        if not self.value or not self.fact_ids:
            raise ValueError("feature content and facts are required")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogFieldResolution:
    field_name: str
    value: str | None
    strategy: FieldPopulationStrategy
    validation_status: FieldValidationStatus
    provenance: FieldProvenance | None
    confidence_bp: int
    review_required: bool
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _confidence(self.confidence_bp)
        if self.value is None and self.provenance is not None:
            raise ValueError("blank field cannot retain populated-field provenance")
        if self.value is not None and self.provenance is None:
            raise ValueError("populated field requires provenance")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogEnrichmentResult:
    enrichment_id: str
    input_row_id: str
    delivery_record: UnilogDeliveryRecord
    field_resolutions: tuple[UnilogFieldResolution, ...]
    attributes: tuple[UnilogSemanticAttributeCandidate, ...]
    features: tuple[UnilogItemFeature, ...]
    descriptions: tuple[UnilogDescriptionResult, ...]
    review_required: bool
    overall_confidence_bp: int
    populated_field_count: int
    supported_field_count: int
    total_field_count: int
    warnings: tuple[str, ...]
    created_at: datetime
    policy_version: str

    def __post_init__(self) -> None:
        if len(self.enrichment_id) != 64 or len(self.input_row_id) != 64:
            raise ValueError("enrichment result identity is invalid")
        _confidence(self.overall_confidence_bp)
        if self.total_field_count != 252:
            raise ValueError("delivery result must report 252 total fields")
        actual = sum(value not in (None, "") for value in self.delivery_record.as_dict().values())
        if self.populated_field_count != actual:
            raise ValueError("populated field coverage is inconsistent")
        if not 0 <= self.supported_field_count <= self.total_field_count:
            raise ValueError("supported field coverage is invalid")
        object.__setattr__(self, "created_at", _aware(self.created_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBatchRowResult:
    input_row_id: str
    input_row: UnilogChallengeInputRow
    status: BatchRowStatus
    enrichment: UnilogEnrichmentResult | None
    error: str | None

    def __post_init__(self) -> None:
        if len(self.input_row_id) != 64:
            raise ValueError("batch row identity is invalid")
        if self.input_row.row_id != self.input_row_id:
            raise ValueError("batch row identity does not match its input")
        if (self.status is BatchRowStatus.FAILED) != (self.error is not None):
            raise ValueError("batch row error and status are inconsistent")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBatchStatistics:
    total: int
    successful: int
    review_required: int
    failed: int
    average_populated_fields: int
    average_confidence_bp: int

    def __post_init__(self) -> None:
        if self.total != self.successful + self.review_required + self.failed:
            raise ValueError("batch statistics counts are inconsistent")
        _confidence(self.average_confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBatchEnrichmentResult:
    rows: tuple[UnilogBatchRowResult, ...]
    statistics: UnilogBatchStatistics


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogDescriptionSignals:
    product_type: str | None
    product_type_span: tuple[int, int] | None
    series: str | None
    series_span: tuple[int, int] | None
    measurements: tuple[UnilogMeasurementCandidate, ...]
    quantity: int | None
    quantity_span: tuple[int, int] | None
    grit: str | None
    grit_span: tuple[int, int] | None
    material: str | None
    material_span: tuple[int, int] | None


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogResolvedFacts:
    _values: Mapping[str, str]

    def __post_init__(self) -> None:
        if any(not key or not value for key, value in self._values.items()):
            raise ValueError("resolved fact keys and values must be nonblank")
        object.__setattr__(self, "_values", MappingProxyType(dict(self._values)))

    def as_dict(self) -> dict[str, str]:
        return dict(self._values)
