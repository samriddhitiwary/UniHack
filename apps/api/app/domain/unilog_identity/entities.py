"""Immutable dataset-derived manufacturer and brand evidence models."""

from dataclasses import dataclass

from app.domain.unilog_challenge.enums import ResolutionStatus
from app.domain.unilog_identity.enums import IdentityEvidenceSource, IdentityReviewReason

UNILOG_IDENTITY_POLICY_VERSION = "unilog-manufacturer-brand-policy-v1"
MAX_IDENTITY_EXAMPLES = 5


def _confidence(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
        raise ValueError("identity confidence must be from 0 through 10000")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogOrganizationEvidence:
    raw_value: str
    clean_value: str
    parsed_name: str
    source_reference_code: str | None
    source_field: IdentityEvidenceSource
    supplier_likelihood_bp: int
    manufacturer_likelihood_bp: int
    evidence_reasons: tuple[str, ...]
    support_count: int = 1
    example_rows: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.raw_value or not self.clean_value or not self.parsed_name:
            raise ValueError("organization evidence values are required")
        _confidence(self.supplier_likelihood_bp)
        _confidence(self.manufacturer_likelihood_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogBrandCandidate:
    raw_value: str
    normalized_value: str
    source_field: IdentityEvidenceSource
    description_span: tuple[int, int] | None
    support_count: int
    product_type_support: tuple[str, ...]
    confidence_bp: int
    review_required: bool

    def __post_init__(self) -> None:
        if not self.raw_value or not self.normalized_value or self.support_count < 1:
            raise ValueError("brand candidate is invalid")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedIdentityVocabularyEntry:
    canonical_observed_value: str
    normalized_variants: tuple[str, ...]
    support_count: int
    source_fields: tuple[IdentityEvidenceSource, ...]
    example_rows: tuple[str, ...]
    confidence_bp: int

    def __post_init__(self) -> None:
        if not self.canonical_observed_value or self.support_count < 1:
            raise ValueError("identity vocabulary entry is invalid")
        if len(self.example_rows) > MAX_IDENTITY_EXAMPLES:
            raise ValueError("identity examples are unbounded")
        _confidence(self.confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class LeadingDescriptionPhraseEvidence:
    normalized_leading_phrase: str
    canonical_phrase: str
    occurrence_count: int
    distinct_product_types: int
    distinct_part_manuf_values: int
    distinct_mpns: int
    associated_brand_candidates: tuple[str, ...]
    confidence_bp: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedMpnPrefixEvidence:
    prefix: str
    support_count: int
    associated_brand_candidates: tuple[str, ...]
    associated_manufacturer_candidates: tuple[str, ...]
    confidence_bp: int


@dataclass(frozen=True, slots=True, kw_only=True)
class IdentityRelationEvidence:
    left_value: str
    right_value: str
    support_count: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ManufacturerResolutionResult:
    manufacturer: str | None
    brand: str | None
    supplier_organization: str | None
    manufacturer_status: ResolutionStatus
    brand_status: ResolutionStatus
    manufacturer_confidence_bp: int
    brand_confidence_bp: int
    manufacturer_evidence: tuple[str, ...]
    brand_evidence: tuple[str, ...]
    review_required: bool
    review_reasons: tuple[IdentityReviewReason, ...]

    def __post_init__(self) -> None:
        _confidence(self.manufacturer_confidence_bp)
        _confidence(self.brand_confidence_bp)


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogIdentityModelProposal:
    manufacturer_candidate: str | None
    brand_candidate: UnilogBrandCandidate | None
    evidence_text: str
    evidence_span: tuple[int, int]
    review_required: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogIdentityVocabularyStatistics:
    input_rows: int
    unique_organizations: int
    supplier_like_organizations: int
    non_placeholder_brand_rows: int
    description_brand_candidates: int
    repeated_mpn_prefixes: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnilogManufacturerBrandEvidenceArtifact:
    policy_version: str
    input_sha256: str
    ground_truth_sha256: str
    artifact_hash: str
    organizations: tuple[UnilogOrganizationEvidence, ...]
    observed_manufacturers: tuple[ObservedIdentityVocabularyEntry, ...]
    observed_brands: tuple[ObservedIdentityVocabularyEntry, ...]
    leading_description_tokens: tuple[LeadingDescriptionPhraseEvidence, ...]
    mpn_prefix_evidence: tuple[ObservedMpnPrefixEvidence, ...]
    manufacturer_brand_relations: tuple[IdentityRelationEvidence, ...]
    supplier_brand_relations: tuple[IdentityRelationEvidence, ...]
    statistics: UnilogIdentityVocabularyStatistics

    def __post_init__(self) -> None:
        if self.policy_version != UNILOG_IDENTITY_POLICY_VERSION:
            raise ValueError("identity policy version is invalid")
        hashes = (self.input_sha256, self.ground_truth_sha256, self.artifact_hash)
        if any(len(item) != 64 for item in hashes):
            raise ValueError("identity artifact hashes are invalid")
