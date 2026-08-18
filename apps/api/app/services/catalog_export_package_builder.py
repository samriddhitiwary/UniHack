"""Build a bounded deterministic three-artifact publication package."""

from datetime import datetime
from uuid import UUID

from app.core.exceptions import (
    CatalogExportAttributeLimitExceededError,
    CatalogExportCsvSizeLimitExceededError,
    CatalogExportJsonSizeLimitExceededError,
    CatalogExportManifestSizeLimitExceededError,
)
from app.domain.catalog_export import (
    CatalogExportArtifact,
    CatalogExportArtifactFormat,
    CatalogExportPackageBuild,
)
from app.domain.catalog_projection import CommerceCatalogProjection
from app.services.catalog_csv_exporter import CatalogCsvExporter
from app.services.catalog_export_checksums import sha256_hex
from app.services.catalog_json_exporter import CatalogJsonExporter
from app.services.catalog_manifest_builder import CatalogManifestBuilder


class CatalogExportPackageBuilder:
    def __init__(
        self,
        *,
        json_exporter: CatalogJsonExporter,
        csv_exporter: CatalogCsvExporter,
        manifest_builder: CatalogManifestBuilder,
        max_json_bytes: int,
        max_csv_bytes: int,
        max_manifest_bytes: int,
        max_attributes: int,
    ) -> None:
        self._json = json_exporter
        self._csv = csv_exporter
        self._manifest = manifest_builder
        self._max_json = max_json_bytes
        self._max_csv = max_csv_bytes
        self._max_manifest = max_manifest_bytes
        self._max_attributes = max_attributes

    def build(
        self,
        *,
        export_id: UUID,
        projection: CommerceCatalogProjection,
        created_at: datetime,
    ) -> CatalogExportPackageBuild:
        if len(projection.attributes) > self._max_attributes:
            raise CatalogExportAttributeLimitExceededError()
        json_bytes = self._json.serialize(projection=projection)
        if len(json_bytes) > self._max_json:
            raise CatalogExportJsonSizeLimitExceededError()
        csv_bytes = self._csv.serialize(projection=projection)
        if len(csv_bytes) > self._max_csv:
            raise CatalogExportCsvSizeLimitExceededError()
        json_artifact = self._artifact(
            export_id, CatalogExportArtifactFormat.CANONICAL_JSON, json_bytes, created_at
        )
        csv_artifact = self._artifact(
            export_id, CatalogExportArtifactFormat.CATALOG_CSV, csv_bytes, created_at
        )
        manifest_bytes = self._manifest.build(
            export_id=export_id,
            projection=projection,
            artifacts_without_manifest=(json_artifact, csv_artifact),
            created_at=created_at,
        )
        if len(manifest_bytes) > self._max_manifest:
            raise CatalogExportManifestSizeLimitExceededError()
        manifest_artifact = self._artifact(
            export_id, CatalogExportArtifactFormat.MANIFEST_JSON, manifest_bytes, created_at
        )
        return CatalogExportPackageBuild(
            export_id=export_id,
            canonical_json=json_bytes,
            catalog_csv=csv_bytes,
            manifest_json=manifest_bytes,
            artifacts=(json_artifact, csv_artifact, manifest_artifact),
        )

    def max_size_for(self, format: CatalogExportArtifactFormat) -> int:
        return {
            CatalogExportArtifactFormat.CANONICAL_JSON: self._max_json,
            CatalogExportArtifactFormat.CATALOG_CSV: self._max_csv,
            CatalogExportArtifactFormat.MANIFEST_JSON: self._max_manifest,
        }[format]

    @staticmethod
    def _artifact(
        export_id: UUID,
        format: CatalogExportArtifactFormat,
        content: bytes,
        created_at: datetime,
    ) -> CatalogExportArtifact:
        names = {
            CatalogExportArtifactFormat.CANONICAL_JSON: ("catalog.json", "application/json"),
            CatalogExportArtifactFormat.CATALOG_CSV: ("catalog.csv", "text/csv"),
            CatalogExportArtifactFormat.MANIFEST_JSON: ("manifest.json", "application/json"),
        }
        file_name, media_type = names[format]
        return CatalogExportArtifact(
            format=format,
            file_name=file_name,
            media_type=media_type,
            object_key=f"catalog-exports/{export_id}/{file_name}",
            size_bytes=len(content),
            sha256=sha256_hex(content),
            created_at=created_at,
        )
