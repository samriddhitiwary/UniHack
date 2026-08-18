"""Immutable review aggregates, decisions, and current projections."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_selection import AttributeSelectionResult
from app.domain.product_review.enums import (
    RESOLVING_DECISION_TYPES,
    AttributeReviewDecisionType,
    ProductReviewSessionStatus,
)
from app.domain.products import ProductCategory


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(UTC)


def _bounded(value: str, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{field} must be nonempty and bounded")
    return value.strip()


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeReviewDecision:
    decision_id: UUID
    review_id: UUID
    product_id: UUID
    decision_sequence: int
    attribute_name: str
    decision_type: AttributeReviewDecisionType
    candidate_id: str | None
    approved_value: str | None
    approved_unit: str | None
    manual_raw_value: str | None
    manual_raw_unit: str | None
    comment: str | None
    reviewer_id: str
    review_version: int
    created_at: datetime

    def __post_init__(self) -> None:
        if self.decision_sequence < 1 or self.review_version < 2:
            raise ValueError("decision sequence or review version is invalid")
        object.__setattr__(
            self, "attribute_name", _bounded(self.attribute_name, "attribute_name", 100)
        )
        object.__setattr__(self, "reviewer_id", _bounded(self.reviewer_id, "reviewer_id", 200))
        if self.comment is not None and len(self.comment) > 2_000:
            raise ValueError("comment is too large")
        resolving = self.decision_type in RESOLVING_DECISION_TYPES
        if resolving and self.approved_value is None:
            raise ValueError("resolving decisions require an approved value")
        if not resolving and any(
            value is not None
            for value in (
                self.candidate_id,
                self.approved_value,
                self.approved_unit,
                self.manual_raw_value,
                self.manual_raw_unit,
            )
        ):
            raise ValueError("reject-all cannot contain approved or candidate values")
        if self.decision_type is AttributeReviewDecisionType.APPROVE_CANDIDATE:
            if not self.candidate_id or self.manual_raw_value is not None:
                raise ValueError("candidate approval fields are inconsistent")
        elif self.decision_type is AttributeReviewDecisionType.APPROVE_PROPOSED:
            if not self.candidate_id or self.manual_raw_value is not None:
                raise ValueError("proposed approval fields are inconsistent")
        elif self.decision_type is AttributeReviewDecisionType.MANUAL_OVERRIDE and (
            self.candidate_id is not None or self.manual_raw_value is None
        ):
            raise ValueError("manual override fields are inconsistent")
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))


@dataclass(frozen=True, slots=True, kw_only=True)
class CurrentAttributeReviewDecision:
    attribute_name: str
    decision_id: UUID
    decision_sequence: int
    decision_type: AttributeReviewDecisionType
    candidate_id: str | None
    approved_value: str | None
    approved_unit: str | None
    reviewer_id: str
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "attribute_name", _bounded(self.attribute_name, "attribute_name", 100)
        )
        object.__setattr__(self, "reviewer_id", _bounded(self.reviewer_id, "reviewer_id", 200))
        if self.decision_sequence < 1:
            raise ValueError("current decision sequence must be positive")
        object.__setattr__(self, "updated_at", _utc(self.updated_at, "updated_at"))

    @classmethod
    def from_decision(cls, decision: AttributeReviewDecision) -> "CurrentAttributeReviewDecision":
        return cls(
            attribute_name=decision.attribute_name,
            decision_id=decision.decision_id,
            decision_sequence=decision.decision_sequence,
            decision_type=decision.decision_type,
            candidate_id=decision.candidate_id,
            approved_value=decision.approved_value,
            approved_unit=decision.approved_unit,
            reviewer_id=decision.reviewer_id,
            updated_at=decision.created_at,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductReviewSession:
    review_id: UUID
    product_id: UUID
    selection_id: UUID
    conflict_detection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    status: ProductReviewSessionStatus
    version: int
    required_attribute_count: int
    required_resolved_count: int
    required_unresolved_count: int
    optional_attribute_count: int
    optional_resolved_count: int
    decision_count: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if (
            self.version < 1
            or min(
                self.required_attribute_count,
                self.required_resolved_count,
                self.required_unresolved_count,
                self.optional_attribute_count,
                self.optional_resolved_count,
                self.decision_count,
            )
            < 0
        ):
            raise ValueError("review version or counts are invalid")
        if (
            self.required_resolved_count + self.required_unresolved_count
            != self.required_attribute_count
        ):
            raise ValueError("required review counts are inconsistent")
        if self.optional_resolved_count > self.optional_attribute_count:
            raise ValueError("optional review counts are inconsistent")
        created, updated = _utc(self.created_at, "created_at"), _utc(self.updated_at, "updated_at")
        if updated < created:
            raise ValueError("updated_at cannot precede created_at")
        if self.status is ProductReviewSessionStatus.COMPLETED:
            if self.completed_at is None or self.required_unresolved_count:
                raise ValueError(
                    "completed reviews require completion time and resolved required attributes"
                )
        elif self.completed_at is not None:
            raise ValueError("open reviews cannot contain completed_at")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "updated_at", updated)
        if self.completed_at is not None:
            object.__setattr__(self, "completed_at", _utc(self.completed_at, "completed_at"))

    @property
    def completion_ready(self) -> bool:
        return self.required_unresolved_count == 0

    @classmethod
    def create(cls, selection: AttributeSelectionResult, now: datetime) -> "ProductReviewSession":
        required = sum(item.required for item in selection.attributes)
        optional = len(selection.attributes) - required
        timestamp = _utc(now, "now")
        return cls(
            review_id=uuid4(),
            product_id=selection.product_id,
            selection_id=selection.selection_id,
            conflict_detection_id=selection.conflict_detection_id,
            validation_id=selection.validation_id,
            completeness_id=selection.completeness_id,
            normalization_id=selection.normalization_id,
            extraction_id=selection.extraction_id,
            classification_id=selection.classification_id,
            category=selection.category,
            schema_version=selection.schema_version,
            schema_fingerprint=selection.schema_fingerprint,
            status=ProductReviewSessionStatus.OPEN,
            version=1,
            required_attribute_count=required,
            required_resolved_count=0,
            required_unresolved_count=required,
            optional_attribute_count=optional,
            optional_resolved_count=0,
            decision_count=0,
            created_at=timestamp,
            updated_at=timestamp,
            completed_at=None,
        )

    def after_decision(
        self, *, required_resolved: int, optional_resolved: int, now: datetime
    ) -> "ProductReviewSession":
        return replace(
            self,
            version=self.version + 1,
            decision_count=self.decision_count + 1,
            required_resolved_count=required_resolved,
            required_unresolved_count=self.required_attribute_count - required_resolved,
            optional_resolved_count=optional_resolved,
            updated_at=_utc(now, "now"),
        )

    def complete(self, now: datetime) -> "ProductReviewSession":
        if not self.completion_ready:
            raise ValueError("required attributes remain unresolved")
        timestamp = _utc(now, "now")
        return replace(
            self,
            status=ProductReviewSessionStatus.COMPLETED,
            version=self.version + 1,
            updated_at=timestamp,
            completed_at=timestamp,
        )


@dataclass(frozen=True, slots=True)
class ReviewDecisionPage:
    items: tuple[AttributeReviewDecision, ...]
    next_cursor: str | None
