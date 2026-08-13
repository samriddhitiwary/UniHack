"""Immutable, traceable product-classification evidence and results."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.product_classification.enums import (
    ClassificationEvidenceType,
    ClassificationSignalStrength,
    ProductClassificationStatus,
)
from app.domain.products import ProductCategory

EXCERPT_MAX_LENGTH = 500
LOCATION_MAX_LENGTH = 500
SIGNAL_MAX_LENGTH = 100
WARNING_CODE_MAX_LENGTH = 100


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassificationEvidence:
    evidence_id: str
    source_id: UUID
    evidence_type: ClassificationEvidenceType
    text: str
    location: str
    weight: int

    def __post_init__(self) -> None:
        if not self.evidence_id or len(self.evidence_id) > 50:
            raise ValueError("evidence_id must be nonempty and bounded")
        if not isinstance(self.source_id, UUID):
            raise ValueError("source_id must be a UUID")
        if not isinstance(self.evidence_type, ClassificationEvidenceType):
            raise ValueError("evidence_type is invalid")
        if not self.text:
            raise ValueError("evidence text must be nonempty")
        if not self.location or len(self.location) > LOCATION_MAX_LENGTH:
            raise ValueError("location must be nonempty and bounded")
        if isinstance(self.weight, bool) or not isinstance(self.weight, int) or self.weight < 0:
            raise ValueError("weight must be a non-negative integer")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClassificationMatch:
    match_id: str
    evidence_id: str
    source_id: UUID
    evidence_type: ClassificationEvidenceType
    category: ProductCategory
    matched_signal: str
    signal_strength: ClassificationSignalStrength
    weighted_score: int
    location: str
    excerpt: str

    def __post_init__(self) -> None:
        if not self.match_id or len(self.match_id) > 50:
            raise ValueError("match_id must be nonempty and bounded")
        if not self.evidence_id or len(self.evidence_id) > 50:
            raise ValueError("evidence_id must be nonempty and bounded")
        if not isinstance(self.source_id, UUID):
            raise ValueError("source_id must be a UUID")
        if self.category not in {
            ProductCategory.CENTRIFUGAL_PUMP,
            ProductCategory.INDUCTION_MOTOR,
        }:
            raise ValueError("match category must be a supported classified category")
        if not self.matched_signal or len(self.matched_signal) > SIGNAL_MAX_LENGTH:
            raise ValueError("matched_signal must be nonempty and bounded")
        if self.weighted_score <= 0:
            raise ValueError("weighted_score must be positive")
        if not self.location or len(self.location) > LOCATION_MAX_LENGTH:
            raise ValueError("location must be nonempty and bounded")
        if not self.excerpt or len(self.excerpt) > EXCERPT_MAX_LENGTH:
            raise ValueError("excerpt must be nonempty and bounded")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductClassificationDecision:
    category: ProductCategory
    status: ProductClassificationStatus
    confidence_bp: int
    pump_score: int
    motor_score: int
    conflicting_evidence_count: int
    matches: tuple[ClassificationMatch, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductClassificationResult:
    classification_id: UUID
    job_id: UUID
    product_id: UUID
    category: ProductCategory
    status: ProductClassificationStatus
    confidence_bp: int
    pump_score: int
    motor_score: int
    evidence_item_count: int
    matched_evidence_count: int
    conflicting_evidence_count: int
    matches: tuple[ClassificationMatch, ...]
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, UUID)
            for value in (self.classification_id, self.job_id, self.product_id)
        ):
            raise ValueError("result identities must be UUIDs")
        if not 0 <= self.confidence_bp <= 10_000:
            raise ValueError("confidence_bp must be between 0 and 10000")
        if (
            min(
                self.pump_score,
                self.motor_score,
                self.evidence_item_count,
                self.matched_evidence_count,
                self.conflicting_evidence_count,
            )
            < 0
        ):
            raise ValueError("result counts and scores must be non-negative")
        if self.matched_evidence_count != len({match.evidence_id for match in self.matches}):
            raise ValueError("matched_evidence_count must match distinct evidence")
        if self.category is ProductCategory.UNCLASSIFIED:
            if self.status is ProductClassificationStatus.CLASSIFIED:
                raise ValueError("UNCLASSIFIED result cannot have CLASSIFIED status")
        elif self.status is not ProductClassificationStatus.CLASSIFIED:
            raise ValueError("classified category requires CLASSIFIED status")
        if not self.engine.strip() or not self.engine_version.strip():
            raise ValueError("engine identity must be nonempty")
        if len(set(self.warning_codes)) != len(self.warning_codes) or any(
            not code or len(code) > WARNING_CODE_MAX_LENGTH for code in self.warning_codes
        ):
            raise ValueError("warning codes must be unique, nonempty, and bounded")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        decision: ProductClassificationDecision,
        evidence_item_count: int,
        now: datetime | None = None,
    ) -> "ProductClassificationResult":
        return cls(
            classification_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            category=decision.category,
            status=decision.status,
            confidence_bp=decision.confidence_bp,
            pump_score=decision.pump_score,
            motor_score=decision.motor_score,
            evidence_item_count=evidence_item_count,
            matched_evidence_count=len({match.evidence_id for match in decision.matches}),
            conflicting_evidence_count=decision.conflicting_evidence_count,
            matches=decision.matches,
            warning_codes=(),
            engine="deterministic-rule-v1",
            engine_version="1.0",
            created_at=now or datetime.now(UTC),
        )
