"""Deterministic canonical JSON serialization for catalog projections."""

import json

from app.core.exceptions import CatalogExportSerializationError
from app.domain.catalog_projection import CommerceCatalogProjection


class CatalogJsonExporter:
    def serialize(self, *, projection: CommerceCatalogProjection) -> bytes:
        try:
            payload = {
                "catalog": {
                    "attributes": [self._attribute(item) for item in projection.attributes],
                    "createdAt": self._timestamp(projection.created_at),
                    "projectionId": str(projection.projection_id),
                    "schemaFingerprint": projection.schema_fingerprint,
                    "schemaVersion": projection.schema_version,
                    "status": projection.status.value,
                    "warningReasonCodes": [
                        reason.value for reason in projection.warning_reason_codes
                    ],
                },
                "lineage": {
                    "classificationId": str(projection.classification_id),
                    "completenessId": str(projection.completeness_id),
                    "conflictDetectionId": str(projection.conflict_detection_id),
                    "extractionId": str(projection.extraction_id),
                    "materializationId": str(projection.materialization_id),
                    "normalizationId": str(projection.normalization_id),
                    "reviewId": str(projection.review_id),
                    "selectionId": str(projection.selection_id),
                    "validationId": str(projection.validation_id),
                },
                "product": {
                    "category": projection.category.value,
                    "description": projection.description,
                    "manufacturer": projection.manufacturer,
                    "modelNumber": projection.model_number,
                    "name": projection.product_name,
                    "productId": str(projection.product_id),
                    "productVersion": projection.product_version,
                },
                "schema": {"name": "catalogiq-commerce-catalog", "version": 1},
            }
            return (
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                + "\n"
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise CatalogExportSerializationError() from exc

    @staticmethod
    def _attribute(item: object) -> dict[str, object]:
        from app.domain.catalog_projection import CommerceCatalogAttribute

        if not isinstance(item, CommerceCatalogAttribute):
            raise TypeError("catalog attribute is invalid")
        return {
            "attributeDisplayName": item.attribute_display_name,
            "attributeName": item.attribute_name,
            "candidateId": item.candidate_id,
            "dataType": item.data_type.value,
            "displayOrder": item.display_order,
            "origin": item.origin.value,
            "required": item.required,
            "reviewDecisionId": str(item.review_decision_id),
            "sourceId": None if item.source_id is None else str(item.source_id),
            "unit": item.unit,
            "validationStatus": (
                None if item.validation_status is None else item.validation_status.value
            ),
            "value": item.value,
        }

    @staticmethod
    def _timestamp(value: object) -> str:
        from datetime import datetime

        if not isinstance(value, datetime):
            raise TypeError("catalog timestamp is invalid")
        return value.isoformat().replace("+00:00", "Z")
