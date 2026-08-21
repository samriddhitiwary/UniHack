"""Immutable dataset-derived vocabulary and evidence-grounded resolution models."""

from dataclasses import dataclass

from app.domain.unilog_classification.enums import (
    AbbreviationStatus,
    ClassificationReviewReason,
    ClasspathMappingSource,
    ProductTypeMatchMethod,
    VocabularySource,
)

UNILOG_CLASSIFICATION_POLICY_VERSION = "unilog-classification-policy-v1"
MAX_VOCABULARY_EXAMPLES = 3


def _confidence(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
        raise ValueError("confidence must be an integer from 0 through 10000")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogProductTypeVocabularyEntry:
    canonical_product_type: str
    normalized_key: str
    product_family: str | None
    variants: tuple[str, ...]
    occurrence_count: int
    source: VocabularySource
    support_count: int
    example_evidence: tuple[str, ...]
    manufacturer_evidence_count: int
    brand_evidence_count: int
    confidence_bp: int

    def __post_init__(self) -> None:
        if not self.canonical_product_type or not self.normalized_key:
            raise ValueError("product type and normalized key are required")
        if self.occurrence_count <= 0 or self.support_count <= 0:
            raise ValueError("vocabulary support counts must be positive")
        if self.support_count != self.occurrence_count:
            raise ValueError("support count must equal observed row occurrence count")
        if not self.variants or len(set(self.variants)) != len(self.variants):
            raise ValueError("vocabulary variants must be nonempty and unique")
        if not 1 <= len(self.example_evidence) <= MAX_VOCABULARY_EXAMPLES:
            raise ValueError("vocabulary evidence examples are invalid")
        if min(self.manufacturer_evidence_count, self.brand_evidence_count) < 0:
            raise ValueError("evidence counts cannot be negative")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogObservedAbbreviation:
    raw_token: str
    expanded_phrase: str
    support_count: int
    evidence_examples: tuple[str, ...]
    confidence_bp: int
    status: AbbreviationStatus

    def __post_init__(self) -> None:
        if not self.raw_token or not self.expanded_phrase or self.support_count < 0:
            raise ValueError("abbreviation values are invalid")
        if len(self.evidence_examples) > MAX_VOCABULARY_EXAMPLES:
            raise ValueError("abbreviation evidence is unbounded")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifiedUnilogClasspathMapping:
    product_type: str
    classpath: str
    department: str | None
    class_name: str | None
    fine: str | None
    mapping_source: ClasspathMappingSource
    support_count: int
    verified: bool
    confidence_bp: int

    def __post_init__(self) -> None:
        if not self.product_type or not self.classpath or self.support_count <= 0:
            raise ValueError("Classpath mapping values are invalid")
        if not self.verified:
            raise ValueError("runtime Classpath mappings must be verified")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogVocabularyStatistics:
    input_rows: int
    unique_descriptions: int
    candidate_product_phrases: int
    canonical_product_types: int
    variants: int
    verified_abbreviations: int
    ambiguous_phrases: int
    generic_only_phrases: int
    verified_classpath_mappings: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogClassificationVocabulary:
    policy_version: str
    input_sha256: str
    vocabulary_hash: str
    entries: tuple[UnilogProductTypeVocabularyEntry, ...]
    abbreviations: tuple[UnilogObservedAbbreviation, ...]
    verified_classpath_mappings: tuple[VerifiedUnilogClasspathMapping, ...]
    unresolved_candidates: tuple[str, ...]
    statistics: UnilogVocabularyStatistics

    def __post_init__(self) -> None:
        if self.policy_version != UNILOG_CLASSIFICATION_POLICY_VERSION:
            raise ValueError("classification policy version is invalid")
        if len(self.input_sha256) != 64 or len(self.vocabulary_hash) != 64:
            raise ValueError("classification vocabulary hashes are invalid")
        keys = [entry.normalized_key for entry in self.entries]
        if keys != sorted(keys) or len(keys) != len(set(keys)):
            raise ValueError("classification vocabulary entries must be unique and sorted")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogProductTypeResolution:
    product_type: str | None
    product_family: str | None
    match_method: ProductTypeMatchMethod
    evidence_span: tuple[int, int] | None
    evidence_text: str | None
    confidence_bp: int
    review_required: bool
    review_reasons: tuple[ClassificationReviewReason, ...]
    candidate_product_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _confidence(self.confidence_bp)
        if self.product_type is None:
            if self.evidence_span is not None or self.evidence_text is not None:
                raise ValueError("unresolved product type cannot retain selected evidence")
        elif self.evidence_span is None or not self.evidence_text:
            raise ValueError("resolved product type requires an evidence span")
        if self.evidence_span is not None and (
            self.evidence_span[0] < 0 or self.evidence_span[1] <= self.evidence_span[0]
        ):
            raise ValueError("product-type evidence span is invalid")
        if len(set(self.review_reasons)) != len(self.review_reasons):
            raise ValueError("classification review reasons must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogClasspathResolution:
    classpath: str | None
    department: str | None
    class_name: str | None
    fine: str | None
    mapping_source: ClasspathMappingSource | None
    confidence_bp: int
    review_required: bool
    review_reasons: tuple[ClassificationReviewReason, ...]

    def __post_init__(self) -> None:
        _confidence(self.confidence_bp)
        if self.classpath is None and any(
            value is not None
            for value in (self.department, self.class_name, self.fine, self.mapping_source)
        ):
            raise ValueError("blank Classpath cannot retain taxonomy mapping values")
        if self.classpath is not None and self.mapping_source is None:
            raise ValueError("populated Classpath requires a verified mapping source")
