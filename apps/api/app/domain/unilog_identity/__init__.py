"""Public SPEC-046 identity evidence domain."""

from app.domain.unilog_identity.entities import (
    UNILOG_IDENTITY_POLICY_VERSION,
    IdentityRelationEvidence,
    LeadingDescriptionPhraseEvidence,
    ManufacturerResolutionResult,
    ObservedIdentityVocabularyEntry,
    ObservedMpnPrefixEvidence,
    UnilogBrandCandidate,
    UnilogIdentityModelProposal,
    UnilogIdentityVocabularyStatistics,
    UnilogManufacturerBrandEvidenceArtifact,
    UnilogOrganizationEvidence,
)
from app.domain.unilog_identity.enums import IdentityEvidenceSource, IdentityReviewReason

__all__ = [
    "UNILOG_IDENTITY_POLICY_VERSION",
    "IdentityEvidenceSource",
    "IdentityRelationEvidence",
    "IdentityReviewReason",
    "LeadingDescriptionPhraseEvidence",
    "ManufacturerResolutionResult",
    "ObservedIdentityVocabularyEntry",
    "ObservedMpnPrefixEvidence",
    "UnilogBrandCandidate",
    "UnilogIdentityModelProposal",
    "UnilogIdentityVocabularyStatistics",
    "UnilogManufacturerBrandEvidenceArtifact",
    "UnilogOrganizationEvidence",
]
