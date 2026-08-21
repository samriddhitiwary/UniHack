"""Immutable metrics for labelled accuracy and unlabelled batch quality."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.unilog_challenge import FieldPopulationStrategy
from app.domain.unilog_evaluation.enums import (
    ConfidenceBand,
    EvaluationMatchStatus,
    FieldIssueType,
    UnilogFieldGroup,
)

UNILOG_EVALUATION_POLICY_VERSION = "unilog-evaluation-policy-v1"


def _rate(value: int) -> None:
    if isinstance(value, bool) or not 0 <= value <= 10_000:
        raise ValueError("rate must be between 0 and 10000 basis points")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogFieldEvaluation:
    field_name: str
    group: UnilogFieldGroup
    expected_value: str | None
    actual_value: str | None
    status: EvaluationMatchStatus
    normalized_method: str | None
    core_enrichment_field: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAccuracyMetrics:
    exact_match_count: int
    normalized_match_count: int
    mismatch_count: int
    expected_populated_actual_blank_count: int
    expected_blank_actual_populated_count: int
    both_blank_count: int
    not_evaluated_count: int
    evaluable_field_count: int
    exact_match_rate_bp: int
    accepted_match_rate_bp: int

    def __post_init__(self) -> None:
        counts = (
            self.exact_match_count,
            self.normalized_match_count,
            self.mismatch_count,
            self.expected_populated_actual_blank_count,
            self.expected_blank_actual_populated_count,
            self.both_blank_count,
            self.not_evaluated_count,
            self.evaluable_field_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("accuracy counts cannot be negative")
        _rate(self.exact_match_rate_bp)
        _rate(self.accepted_match_rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogGroupMetrics:
    group: UnilogFieldGroup
    accuracy: UnilogAccuracyMetrics
    labelled_populated_count: int
    generated_populated_count: int
    coverage_rate_bp: int

    def __post_init__(self) -> None:
        _rate(self.coverage_rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeMetrics:
    expected_attribute_count: int
    generated_attribute_count: int
    matched_label_count: int
    matched_value_count: int
    matched_uom_count: int
    matched_triple_count: int
    position_exact_cell_count: int
    position_evaluable_cell_count: int
    precision_bp: int | None
    recall_bp: int | None
    f1_bp: int | None
    label_accuracy_bp: int | None
    value_accuracy_bp: int | None
    uom_accuracy_bp: int | None
    triple_accuracy_bp: int | None

    def __post_init__(self) -> None:
        for value in (
            self.precision_bp,
            self.recall_bp,
            self.f1_bp,
            self.label_accuracy_bp,
            self.value_accuracy_bp,
            self.uom_accuracy_bp,
            self.triple_accuracy_bp,
        ):
            if value is not None:
                _rate(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogStrategyCoverage:
    strategy: FieldPopulationStrategy
    populated_count: int
    possible_count: int
    coverage_rate_bp: int

    def __post_init__(self) -> None:
        _rate(self.coverage_rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBlankFieldMetric:
    field_name: str
    group: UnilogFieldGroup
    blank_count: int
    total_rows: int
    blank_rate_bp: int

    def __post_init__(self) -> None:
        _rate(self.blank_rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogCoverageMetrics:
    row_count: int
    average_populated_fields_bp: int
    median_populated_fields: int
    minimum_populated_fields: int
    maximum_populated_fields: int
    raw_coverage_rate_bp: int
    supported_field_count: int
    supported_coverage_rate_bp: int
    strategy_coverage: tuple[UnilogStrategyCoverage, ...]
    most_blank_supported_fields: tuple[UnilogBlankFieldMetric, ...]
    external_or_unsupported_blank_rate_bp: int

    def __post_init__(self) -> None:
        for value in (
            self.raw_coverage_rate_bp,
            self.supported_coverage_rate_bp,
            self.external_or_unsupported_blank_rate_bp,
        ):
            _rate(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogDescriptionFieldMetrics:
    field_name: str
    populated_count: int
    non_empty_rate_bp: int
    grounding_compliance_bp: int
    numeric_traceability_bp: int
    duplicate_token_warning_count: int

    def __post_init__(self) -> None:
        _rate(self.non_empty_rate_bp)
        _rate(self.grounding_compliance_bp)
        _rate(self.numeric_traceability_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogDescriptionComplianceMetrics:
    invoice_populated_count: int
    invoice_uppercase_compliance_bp: int
    invoice_max_40_compliance_bp: int
    invoice_non_empty_rate_bp: int
    mobile_populated_count: int
    mobile_preferred_length_rate_bp: int
    mobile_under_60_rate_bp: int
    mobile_over_80_rate_bp: int
    grounding_compliance_bp: int
    numeric_traceability_bp: int
    unsupported_fact_violation_count: int
    fields: tuple[UnilogDescriptionFieldMetrics, ...]

    def __post_init__(self) -> None:
        for value in (
            self.invoice_uppercase_compliance_bp,
            self.invoice_max_40_compliance_bp,
            self.invoice_non_empty_rate_bp,
            self.mobile_preferred_length_rate_bp,
            self.mobile_under_60_rate_bp,
            self.mobile_over_80_rate_bp,
            self.grounding_compliance_bp,
            self.numeric_traceability_bp,
        ):
            _rate(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogConfidenceBandMetric:
    band: ConfidenceBand
    count: int
    rate_bp: int

    def __post_init__(self) -> None:
        _rate(self.rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogReviewMetrics:
    review_required_count: int
    review_required_rate_bp: int
    reason_counts: tuple[tuple[str, int], ...]
    average_confidence_bp: int
    median_confidence_bp: int
    confidence_bands: tuple[UnilogConfidenceBandMetric, ...]

    def __post_init__(self) -> None:
        _rate(self.review_required_rate_bp)
        _rate(self.average_confidence_bp)
        _rate(self.median_confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBatchQualityMetrics:
    total_rows: int
    processed_rows: int
    review_required_rows: int
    failed_rows: int
    processing_success_rate_bp: int
    failure_rate_bp: int

    def __post_init__(self) -> None:
        _rate(self.processing_success_rate_bp)
        _rate(self.failure_rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogProductTypeFrequency:
    product_type: str
    count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogClassificationMetrics:
    total_rows: int
    resolved_product_type_count: int
    unresolved_product_type_count: int
    product_type_coverage_bp: int
    verified_classpath_count: int
    verified_classpath_coverage_bp: int
    review_required_count: int
    review_required_rate_bp: int
    reason_counts: tuple[tuple[str, int], ...]
    top_product_types: tuple[UnilogProductTypeFrequency, ...]

    def __post_init__(self) -> None:
        if self.total_rows != self.resolved_product_type_count + self.unresolved_product_type_count:
            raise ValueError("classification row counts are inconsistent")
        _rate(self.product_type_coverage_bp)
        _rate(self.verified_classpath_coverage_bp)
        _rate(self.review_required_rate_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeLabelFrequency:
    label: str
    count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeCoverageMetrics:
    total_rows: int
    products_with_attributes: int
    attribute_coverage_bp: int
    official_attributes_resolved: int
    average_attributes_per_product_bp: int
    semantic_candidates_extracted: int
    unknown_semantic_labels: int
    conflicts: int
    unit_ambiguities: int
    overflow_count: int
    review_reason_counts: tuple[tuple[str, int], ...]
    top_attribute_labels: tuple[UnilogAttributeLabelFrequency, ...]

    def __post_init__(self) -> None:
        if (
            min(
                self.total_rows,
                self.products_with_attributes,
                self.official_attributes_resolved,
                self.average_attributes_per_product_bp,
                self.semantic_candidates_extracted,
            )
            < 0
        ):
            raise ValueError("attribute coverage counts cannot be negative")
        _rate(self.attribute_coverage_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogIdentityResolutionMetrics:
    total_rows: int
    manufacturer_resolved: int
    manufacturer_resolution_coverage_bp: int
    manufacturer_ambiguous: int
    brand_resolved: int
    brand_resolution_coverage_bp: int
    brand_ambiguous: int
    supplier_only_rows: int
    manufacturer_exact_labelled: int
    brand_exact_labelled: int
    labelled_rows: int
    review_reason_counts: tuple[tuple[str, int], ...]
    evidence_source_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        _rate(self.manufacturer_resolution_coverage_bp)
        _rate(self.brand_resolution_coverage_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogFieldMetric:
    field_name: str
    group: UnilogFieldGroup
    exact_count: int
    normalized_count: int
    mismatch_count: int
    missing_expected_count: int
    unexpected_populated_count: int
    both_blank_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogFieldProblem:
    field_name: str
    group: UnilogFieldGroup
    issue_type: FieldIssueType
    affected_labelled_rows: int
    priority_score: int
    supported: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogImprovementRecommendation:
    code: str
    title: str
    description: str
    priority_score: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogLabelledRowEvaluation:
    input_row_id: str
    mfg_part_num: str
    comparisons: tuple[UnilogFieldEvaluation, ...]
    accuracy: UnilogAccuracyMetrics


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogEvaluationResult:
    evaluation_id: str
    dataset_fingerprint: str
    generated_batch_fingerprint: str
    policy_version: str
    labelled_row_count: int
    accuracy: UnilogAccuracyMetrics
    group_metrics: tuple[UnilogGroupMetrics, ...]
    attribute_metrics: UnilogAttributeMetrics
    coverage_metrics: UnilogCoverageMetrics
    description_metrics: UnilogDescriptionComplianceMetrics
    review_metrics: UnilogReviewMetrics
    batch_metrics: UnilogBatchQualityMetrics
    classification_metrics: UnilogClassificationMetrics
    attribute_coverage_metrics: UnilogAttributeCoverageMetrics
    identity_resolution_metrics: UnilogIdentityResolutionMetrics
    field_metrics: tuple[UnilogFieldMetric, ...]
    problems: tuple[UnilogFieldProblem, ...]
    recommendations: tuple[UnilogImprovementRecommendation, ...]
    labelled_rows: tuple[UnilogLabelledRowEvaluation, ...]
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.evaluation_id) != 64 or len(self.dataset_fingerprint) != 64:
            raise ValueError("evaluation identity is invalid")
        if len(self.generated_batch_fingerprint) != 64:
            raise ValueError("generated batch fingerprint is invalid")
        if self.policy_version != UNILOG_EVALUATION_POLICY_VERSION:
            raise ValueError("evaluation policy version is invalid")
        if self.labelled_row_count != len(self.labelled_rows):
            raise ValueError("labelled row count is inconsistent")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("evaluation timestamp must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))
