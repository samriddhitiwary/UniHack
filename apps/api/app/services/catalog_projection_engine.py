"""Compose an immutable commerce catalog projection from authoritative local inputs."""

from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    CatalogProjectionCategoryMismatchError,
    CatalogProjectionCrossProductLineageError,
    CatalogProjectionLineageInvalidError,
)
from app.domain.catalog_projection import CommerceCatalogProjection
from app.domain.products import Product
from app.domain.reviewed_attributes import FinalReviewedAttributeSet
from app.services.catalog_product_identity_projector import CatalogProductIdentityProjector
from app.services.catalog_publishing_readiness import CatalogPublishingReadinessEvaluator
from app.services.catalog_reviewed_attribute_projector import (
    CatalogReviewedAttributeProjector,
)


class CatalogProjectionEngine:
    def __init__(
        self,
        *,
        identity_projector: CatalogProductIdentityProjector,
        attribute_projector: CatalogReviewedAttributeProjector,
        readiness_evaluator: CatalogPublishingReadinessEvaluator,
    ) -> None:
        self._identity = identity_projector
        self._attributes = attribute_projector
        self._readiness = readiness_evaluator

    def project(
        self,
        *,
        job_id: UUID,
        product: Product,
        materialization: FinalReviewedAttributeSet,
        now: datetime | None = None,
    ) -> CommerceCatalogProjection:
        if materialization.product_id != product.product_id:
            raise CatalogProjectionCrossProductLineageError()
        if materialization.category != product.category:
            raise CatalogProjectionCategoryMismatchError()
        if (
            materialization.schema_version < 1
            or len(materialization.schema_fingerprint) != 64
            or not all(
                isinstance(value, UUID)
                for value in (
                    materialization.review_id,
                    materialization.selection_id,
                    materialization.validation_id,
                    materialization.completeness_id,
                    materialization.conflict_detection_id,
                    materialization.normalization_id,
                    materialization.extraction_id,
                    materialization.classification_id,
                )
            )
        ):
            raise CatalogProjectionLineageInvalidError()
        identity = self._identity.project(product)
        reviewed = self._attributes.project(materialization)
        status, blockers, warnings = self._readiness.evaluate(
            blockers=identity.blockers,
            warnings=(*identity.warnings, *reviewed.warnings),
        )
        timestamp = (now or datetime.now(UTC)).astimezone(UTC)
        return CommerceCatalogProjection.create(
            job_id=job_id,
            identity=identity.identity,
            attributes=reviewed.attributes,
            status=status,
            blockers=blockers,
            warnings=warnings,
            required_count=materialization.required_attribute_count,
            optional_count=materialization.optional_attribute_count,
            unresolved_optional_count=materialization.unresolved_optional_count,
            materialization_id=materialization.materialization_id,
            review_id=materialization.review_id,
            selection_id=materialization.selection_id,
            validation_id=materialization.validation_id,
            completeness_id=materialization.completeness_id,
            conflict_detection_id=materialization.conflict_detection_id,
            normalization_id=materialization.normalization_id,
            extraction_id=materialization.extraction_id,
            classification_id=materialization.classification_id,
            schema_version=materialization.schema_version,
            schema_fingerprint=materialization.schema_fingerprint,
            now=timestamp,
        )
