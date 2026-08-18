"""Deterministic publication package manifest serialization."""

import json
from datetime import datetime
from uuid import UUID

from app.core.exceptions import CatalogExportSerializationError
from app.domain.catalog_export import CatalogExportArtifact
from app.domain.catalog_projection import CommerceCatalogProjection


class CatalogManifestBuilder:
    def build(
        self,
        *,
        export_id: UUID,
        projection: CommerceCatalogProjection,
        artifacts_without_manifest: tuple[CatalogExportArtifact, ...],
        created_at: datetime,
    ) -> bytes:
        try:
            payload = {
                "artifacts": [
                    {
                        "fileName": artifact.file_name,
                        "format": artifact.format.value,
                        "mediaType": artifact.media_type,
                        "sha256": artifact.sha256,
                        "sizeBytes": artifact.size_bytes,
                    }
                    for artifact in artifacts_without_manifest
                ],
                "createdAt": created_at.isoformat().replace("+00:00", "Z"),
                "exportId": str(export_id),
                "packageVersion": 1,
                "productId": str(projection.product_id),
                "projectionId": str(projection.projection_id),
                "projectionStatus": projection.status.value,
                "warningReasonCodes": [reason.value for reason in projection.warning_reason_codes],
            }
            return (
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
                + "\n"
            ).encode("utf-8")
        except (TypeError, ValueError, UnicodeError) as exc:
            raise CatalogExportSerializationError() from exc
