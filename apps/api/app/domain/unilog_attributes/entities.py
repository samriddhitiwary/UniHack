"""Immutable observed attribute vocabulary and indexed rule models."""

from dataclasses import dataclass

from app.domain.unilog_attributes.enums import AttributeVocabularySource

UNILOG_ATTRIBUTE_POLICY_VERSION = "unilog-attribute-policy-v1"
MAX_ATTRIBUTE_EVIDENCE_VALUES = 10


def _confidence(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
        raise ValueError("confidence must be an integer from 0 through 10000")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogObservedAttributeDefinition:
    label: str
    normalized_label: str
    observed_values: tuple[str, ...]
    observed_uoms: tuple[str, ...]
    observed_product_types: tuple[str, ...]
    support_count: int
    source: AttributeVocabularySource

    def __post_init__(self) -> None:
        if not self.label or not self.normalized_label or self.support_count <= 0:
            raise ValueError("observed attribute definition is invalid")
        if len(self.observed_values) > MAX_ATTRIBUTE_EVIDENCE_VALUES:
            raise ValueError("observed attribute values are unbounded")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogObservedUomResolution:
    raw_uom: str
    normalized_uom: str
    source: AttributeVocabularySource
    confidence_bp: int
    review_required: bool

    def __post_init__(self) -> None:
        if not self.raw_uom or not self.normalized_uom:
            raise ValueError("observed UOM resolution is invalid")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class SemanticAttributeToObservedLabelMapping:
    semantic_name: str
    observed_label: str
    source: AttributeVocabularySource
    confidence_bp: int

    def __post_init__(self) -> None:
        if not self.semantic_name or not self.observed_label:
            raise ValueError("semantic attribute mapping is invalid")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeProductTypeRule:
    product_type: str
    semantic_attributes: tuple[str, ...]
    dimension_order: tuple[str, ...]
    supports_quantity: bool
    supports_grit: bool
    map_dimensions_to_size: bool
    priority: int

    def __post_init__(self) -> None:
        if not self.product_type or not 0 <= self.priority <= 100:
            raise ValueError("product-type attribute rule is invalid")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeVocabularyStatistics:
    input_rows: int
    labelled_rows: int
    observed_labels: int
    observed_uoms: int
    semantic_mappings: int
    product_type_rules: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogAttributeVocabulary:
    policy_version: str
    input_sha256: str
    ground_truth_sha256: str
    artifact_hash: str
    observed_labels: tuple[UnilogObservedAttributeDefinition, ...]
    observed_uoms: tuple[UnilogObservedUomResolution, ...]
    normalization_mappings: tuple[UnilogObservedUomResolution, ...]
    semantic_mappings: tuple[SemanticAttributeToObservedLabelMapping, ...]
    product_type_rules: tuple[UnilogAttributeProductTypeRule, ...]
    statistics: UnilogAttributeVocabularyStatistics

    def __post_init__(self) -> None:
        if self.policy_version != UNILOG_ATTRIBUTE_POLICY_VERSION:
            raise ValueError("attribute policy version is invalid")
        if any(
            len(value) != 64
            for value in (self.input_sha256, self.ground_truth_sha256, self.artifact_hash)
        ):
            raise ValueError("attribute vocabulary hashes are invalid")
        labels = [item.normalized_label for item in self.observed_labels]
        if labels != sorted(labels) or len(labels) != len(set(labels)):
            raise ValueError("observed attribute labels must be unique and sorted")
