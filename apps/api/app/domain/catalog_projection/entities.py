"""Immutable commerce catalog projection domain models."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.attribute_validation import CandidateValidationStatus
from app.domain.catalog_projection.enums import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.domain.reviewed_attributes import FinalAttributeOrigin


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProductIdentitySnapshot:
    product_id: UUID
    product_version: int
    product_name: str
    manufacturer: str | None
    model_number: str | None
    category: ProductCategory
    description: str | None

    def __post_init__(self) -> None:
        if self.product_version < 1:
            raise ValueError("product version must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class CommerceCatalogAttribute:
    attribute_name: str
    attribute_display_name: str
    data_type: AttributeDataType
    required: bool
    display_order: int
    value: str
    unit: str | None
    origin: FinalAttributeOrigin
    review_decision_id: UUID
    candidate_id: str | None
    source_id: UUID | None
    validation_status: CandidateValidationStatus | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.attribute_name or not self.attribute_display_name or not self.value:
            raise ValueError("catalog attribute identity and value are required")
        if self.display_order < 1:
            raise ValueError("catalog attribute display order must be positive")
        candidate_origin = self.origin in {
            FinalAttributeOrigin.APPROVED_PROPOSED,
            FinalAttributeOrigin.APPROVED_CANDIDATE,
        }
        if candidate_origin and (
            self.candidate_id is None or self.source_id is None or self.validation_status is None
        ):
            raise ValueError("candidate catalog lineage is invalid")
        if self.origin is FinalAttributeOrigin.HUMAN_OVERRIDE and (
            self.candidate_id is not None
            or self.source_id is not None
            or self.validation_status is not None
        ):
            raise ValueError("human override catalog lineage is invalid")
        object.__setattr__(self, "created_at", _utc(self.created_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class CommerceCatalogProjection:
    projection_id: UUID
    job_id: UUID
    product_id: UUID
    product_version: int
    materialization_id: UUID
    review_id: UUID
    selection_id: UUID
    validation_id: UUID
    completeness_id: UUID
    conflict_detection_id: UUID
    normalization_id: UUID
    extraction_id: UUID
    classification_id: UUID
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    product_name: str
    manufacturer: str | None
    model_number: str | None
    description: str | None
    status: CatalogProjectionStatus
    attribute_count: int
    required_attribute_count: int
    optional_attribute_count: int
    unresolved_optional_count: int
    blocking_reason_codes: tuple[CatalogBlockingReason, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    attributes: tuple[CommerceCatalogAttribute, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        required = sum(item.required for item in self.attributes)
        optional = self.attribute_count - required
        if self.product_version < 1 or self.schema_version < 1:
            raise ValueError("catalog projection versions must be positive")
        if len(self.schema_fingerprint) != 64:
            raise ValueError("catalog projection schema fingerprint is invalid")
        if self.attribute_count != len(self.attributes) or len(
            {item.attribute_name for item in self.attributes}
        ) != len(self.attributes):
            raise ValueError("catalog attribute count or uniqueness is invalid")
        if required != self.required_attribute_count:
            raise ValueError("catalog required attribute count is inconsistent")
        if optional + self.unresolved_optional_count != self.optional_attribute_count:
            raise ValueError("catalog optional attribute count is inconsistent")
        if tuple(sorted(self.attributes, key=lambda item: item.display_order)) != self.attributes:
            raise ValueError("catalog attributes must follow display order")
        if len(set(self.blocking_reason_codes)) != len(self.blocking_reason_codes) or len(
            set(self.warning_reason_codes)
        ) != len(self.warning_reason_codes):
            raise ValueError("catalog reason codes must be unique")
        if self.status is CatalogProjectionStatus.BLOCKED and not self.blocking_reason_codes:
            raise ValueError("blocked projections require a blocking reason")
        if self.status is CatalogProjectionStatus.READY_WITH_WARNINGS and (
            self.blocking_reason_codes or not self.warning_reason_codes
        ):
            raise ValueError("warning-ready projection reasons are invalid")
        if self.status is CatalogProjectionStatus.READY and (
            self.blocking_reason_codes or self.warning_reason_codes
        ):
            raise ValueError("ready projections cannot contain reasons")
        object.__setattr__(self, "created_at", _utc(self.created_at))

    @classmethod
    def create(
        cls,
        *,
        job_id: UUID,
        identity: ProductIdentitySnapshot,
        attributes: tuple[CommerceCatalogAttribute, ...],
        status: CatalogProjectionStatus,
        blockers: tuple[CatalogBlockingReason, ...],
        warnings: tuple[CatalogWarningReason, ...],
        required_count: int,
        optional_count: int,
        unresolved_optional_count: int,
        now: datetime,
        **lineage: object,
    ) -> "CommerceCatalogProjection":
        return cls(
            projection_id=uuid4(),
            job_id=job_id,
            product_id=identity.product_id,
            product_version=identity.product_version,
            product_name=identity.product_name,
            manufacturer=identity.manufacturer,
            model_number=identity.model_number,
            category=identity.category,
            description=identity.description,
            status=status,
            attribute_count=len(attributes),
            required_attribute_count=required_count,
            optional_attribute_count=optional_count,
            unresolved_optional_count=unresolved_optional_count,
            blocking_reason_codes=blockers,
            warning_reason_codes=warnings,
            attributes=attributes,
            engine="deterministic-commerce-catalog-projector-v1",
            engine_version="1.0",
            created_at=now,
            **lineage,  # type: ignore[arg-type]
        )
