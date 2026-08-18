"""Immutable proposed selections and product review-preparation result."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_conflicts import AttributeConflictType, AttributeConsensusStatus
from app.domain.attribute_selection.enums import (
    AttributeSelectionStatus,
    ProductReviewStatus,
    SelectionReasonCode,
)
from app.domain.products import ProductCategory


@dataclass(frozen=True, slots=True, kw_only=True)
class ProposedAttributeSelection:
    attribute_name: str
    attribute_display_name: str
    required: bool
    display_order: int
    selection_status: AttributeSelectionStatus
    review_required: bool
    proposed_value: str | None
    proposed_unit: str | None
    primary_candidate_id: str | None
    supporting_candidate_ids: tuple[str, ...]
    review_candidate_ids: tuple[str, ...]
    candidate_count: int
    valid_candidate_count: int
    distinct_source_count: int
    consensus_status: AttributeConsensusStatus | None
    conflict_type: AttributeConflictType | None
    selection_confidence_bp: int
    reason_codes: tuple[SelectionReasonCode, ...]
    warning_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.attribute_name or not self.attribute_display_name or self.display_order < 1:
            raise ValueError("selection attribute identity is invalid")
        if not 0 <= self.valid_candidate_count <= self.candidate_count:
            raise ValueError("selection candidate counts are invalid")
        if not 0 <= self.distinct_source_count <= self.candidate_count:
            raise ValueError("selection source count is invalid")
        if not 0 <= self.selection_confidence_bp <= 10_000:
            raise ValueError("selection confidence must be between 0 and 10000")
        if len(set(self.supporting_candidate_ids)) != len(self.supporting_candidate_ids) or len(
            set(self.review_candidate_ids)
        ) != len(self.review_candidate_ids):
            raise ValueError("selection candidate identifiers must be unique")
        if not self.reason_codes or len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("selection reason codes are invalid")
        if self.selection_status is AttributeSelectionStatus.AUTO_SELECTED:
            if (
                self.review_required
                or self.proposed_value is None
                or self.primary_candidate_id is None
            ):
                raise ValueError(
                    "auto-selected attributes require a proposal and primary candidate"
                )
            if (
                self.primary_candidate_id not in self.supporting_candidate_ids
                or not self.supporting_candidate_ids
            ):
                raise ValueError("primary candidate must be supported")
            if self.review_candidate_ids:
                raise ValueError("auto-selected attributes cannot carry review candidates")
        elif (
            self.proposed_value is not None
            or self.proposed_unit is not None
            or self.primary_candidate_id is not None
            or self.supporting_candidate_ids
        ):
            raise ValueError("only auto-selected attributes may contain a proposal")
        if (
            self.selection_status is AttributeSelectionStatus.REVIEW_REQUIRED
            and not self.review_required
        ):
            raise ValueError("review-required status must require review")
        if (
            self.required
            and self.selection_status is not AttributeSelectionStatus.AUTO_SELECTED
            and not self.review_required
        ):
            raise ValueError("required unresolved attributes must require review")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductReviewPreparationSummary:
    required_attribute_count: int
    auto_selected_required_count: int
    review_required_required_count: int
    missing_required_count: int
    invalid_required_count: int
    optional_attribute_count: int
    auto_selected_optional_count: int
    review_required_optional_count: int
    unresolved_optional_count: int
    auto_selected_total_count: int
    review_required_total_count: int
    overall_status: ProductReviewStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class AttributeSelectionResult:
    selection_id: UUID
    job_id: UUID
    product_id: UUID
    conflict_detection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    overall_status: ProductReviewStatus
    attribute_count: int
    auto_selected_count: int
    review_required_count: int
    no_candidate_count: int
    no_valid_candidate_count: int
    required_auto_selected_count: int
    required_review_required_count: int
    required_missing_count: int
    required_invalid_count: int
    attributes: tuple[ProposedAttributeSelection, ...]
    review_summary: ProductReviewPreparationSummary
    warning_codes: tuple[str, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.attribute_count != len(self.attributes):
            raise ValueError("selection attribute count is inconsistent")
        status_counts = {
            AttributeSelectionStatus.AUTO_SELECTED: self.auto_selected_count,
            AttributeSelectionStatus.REVIEW_REQUIRED: self.review_required_count,
            AttributeSelectionStatus.NO_CANDIDATE: self.no_candidate_count,
            AttributeSelectionStatus.NO_VALID_CANDIDATE: self.no_valid_candidate_count,
        }
        if any(
            value != sum(a.selection_status is status for a in self.attributes)
            for status, value in status_counts.items()
        ):
            raise ValueError("selection status counts are inconsistent")
        required = tuple(a for a in self.attributes if a.required)
        if (
            self.required_auto_selected_count
            != sum(a.selection_status is AttributeSelectionStatus.AUTO_SELECTED for a in required)
            or self.required_review_required_count != sum(a.review_required for a in required)
            or self.required_missing_count
            != sum(a.selection_status is AttributeSelectionStatus.NO_CANDIDATE for a in required)
            or self.required_invalid_count
            != sum(
                a.selection_status is AttributeSelectionStatus.NO_VALID_CANDIDATE for a in required
            )
        ):
            raise ValueError("required selection counts are inconsistent")
        if self.review_summary != build_review_summary(self.attributes):
            raise ValueError("review summary is inconsistent")
        if self.overall_status is not self.review_summary.overall_status:
            raise ValueError("overall selection status is inconsistent")
        if tuple(sorted(self.attributes, key=lambda value: value.display_order)) != self.attributes:
            raise ValueError("selection attributes must follow schema order")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "created_at", self.created_at.astimezone(UTC))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        product_id: UUID,
        conflict_detection_id: UUID,
        validation_id: UUID,
        completeness_id: UUID,
        normalization_id: UUID,
        extraction_id: UUID,
        classification_id: UUID,
        category: ProductCategory,
        schema_version: int,
        schema_fingerprint: str,
        attributes: tuple[ProposedAttributeSelection, ...],
        now: datetime,
    ) -> "AttributeSelectionResult":
        summary = build_review_summary(attributes)
        required = tuple(a for a in attributes if a.required)
        return cls(
            selection_id=uuid4(),
            job_id=job_id,
            product_id=product_id,
            conflict_detection_id=conflict_detection_id,
            validation_id=validation_id,
            completeness_id=completeness_id,
            normalization_id=normalization_id,
            extraction_id=extraction_id,
            classification_id=classification_id,
            category=category,
            schema_version=schema_version,
            schema_fingerprint=schema_fingerprint,
            overall_status=summary.overall_status,
            attribute_count=len(attributes),
            auto_selected_count=sum(
                a.selection_status is AttributeSelectionStatus.AUTO_SELECTED for a in attributes
            ),
            review_required_count=sum(
                a.selection_status is AttributeSelectionStatus.REVIEW_REQUIRED for a in attributes
            ),
            no_candidate_count=sum(
                a.selection_status is AttributeSelectionStatus.NO_CANDIDATE for a in attributes
            ),
            no_valid_candidate_count=sum(
                a.selection_status is AttributeSelectionStatus.NO_VALID_CANDIDATE
                for a in attributes
            ),
            required_auto_selected_count=sum(
                a.selection_status is AttributeSelectionStatus.AUTO_SELECTED for a in required
            ),
            required_review_required_count=sum(a.review_required for a in required),
            required_missing_count=sum(
                a.selection_status is AttributeSelectionStatus.NO_CANDIDATE for a in required
            ),
            required_invalid_count=sum(
                a.selection_status is AttributeSelectionStatus.NO_VALID_CANDIDATE for a in required
            ),
            attributes=attributes,
            review_summary=summary,
            warning_codes=tuple(
                dict.fromkeys(code for a in attributes for code in a.warning_codes)
            ),
            engine="deterministic-attribute-selector-v1",
            engine_version="1.0",
            created_at=now,
        )


def build_review_summary(
    attributes: tuple[ProposedAttributeSelection, ...],
) -> ProductReviewPreparationSummary:
    required = tuple(a for a in attributes if a.required)
    optional = tuple(a for a in attributes if not a.required)
    missing = sum(a.selection_status is AttributeSelectionStatus.NO_CANDIDATE for a in required)
    invalid = sum(
        a.selection_status is AttributeSelectionStatus.NO_VALID_CANDIDATE for a in required
    )
    overall = (
        ProductReviewStatus.INSUFFICIENT_DATA
        if missing or invalid
        else ProductReviewStatus.REVIEW_REQUIRED
        if any(a.review_required for a in required)
        else ProductReviewStatus.READY_FOR_AUTO_APPROVAL
    )
    return ProductReviewPreparationSummary(
        required_attribute_count=len(required),
        auto_selected_required_count=sum(
            a.selection_status is AttributeSelectionStatus.AUTO_SELECTED for a in required
        ),
        review_required_required_count=sum(a.review_required for a in required),
        missing_required_count=missing,
        invalid_required_count=invalid,
        optional_attribute_count=len(optional),
        auto_selected_optional_count=sum(
            a.selection_status is AttributeSelectionStatus.AUTO_SELECTED for a in optional
        ),
        review_required_optional_count=sum(a.review_required for a in optional),
        unresolved_optional_count=sum(
            a.selection_status
            in {AttributeSelectionStatus.NO_CANDIDATE, AttributeSelectionStatus.NO_VALID_CANDIDATE}
            for a in optional
        ),
        auto_selected_total_count=sum(
            a.selection_status is AttributeSelectionStatus.AUTO_SELECTED for a in attributes
        ),
        review_required_total_count=sum(a.review_required for a in attributes),
        overall_status=overall,
    )
