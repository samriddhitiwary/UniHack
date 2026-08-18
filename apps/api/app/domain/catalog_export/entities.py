"""Immutable catalog export package and persistence models."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import InvalidObjectKeyError
from app.domain.catalog_export.enums import CatalogExportArtifactFormat, CatalogExportStatus
from app.domain.catalog_projection import CatalogProjectionStatus, CatalogWarningReason
from app.domain.products import ProductCategory
from app.storage.keys import validate_object_key

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FILE_NAMES = {
    CatalogExportArtifactFormat.CANONICAL_JSON: "catalog.json",
    CatalogExportArtifactFormat.CATALOG_CSV: "catalog.csv",
    CatalogExportArtifactFormat.MANIFEST_JSON: "manifest.json",
}
_MEDIA_TYPES = {
    CatalogExportArtifactFormat.CANONICAL_JSON: "application/json",
    CatalogExportArtifactFormat.CATALOG_CSV: "text/csv",
    CatalogExportArtifactFormat.MANIFEST_JSON: "application/json",
}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("catalog export timestamp must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogExportArtifact:
    format: CatalogExportArtifactFormat
    file_name: str
    media_type: str
    object_key: str
    size_bytes: int
    sha256: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.format, CatalogExportArtifactFormat):
            raise ValueError("catalog export artifact format is invalid")
        if self.file_name != _FILE_NAMES[self.format]:
            raise ValueError("catalog export artifact filename is invalid")
        if self.media_type != _MEDIA_TYPES[self.format]:
            raise ValueError("catalog export artifact media type is invalid")
        try:
            validate_object_key(self.object_key)
        except InvalidObjectKeyError as exc:
            raise ValueError("catalog export artifact object key is invalid") from exc
        if isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int):
            raise ValueError("catalog export artifact size must be an integer")
        if self.size_bytes < 1:
            raise ValueError("catalog export artifact size must be positive")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("catalog export artifact checksum is invalid")
        object.__setattr__(self, "created_at", _utc(self.created_at))


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogExportPackageBuild:
    export_id: UUID
    canonical_json: bytes
    catalog_csv: bytes
    manifest_json: bytes
    artifacts: tuple[CatalogExportArtifact, ...]

    def __post_init__(self) -> None:
        formats = tuple(artifact.format for artifact in self.artifacts)
        if formats != tuple(CatalogExportArtifactFormat):
            raise ValueError("catalog export package must contain exactly three ordered artifacts")
        if not all((self.canonical_json, self.catalog_csv, self.manifest_json)):
            raise ValueError("catalog export package artifacts must not be empty")

    def content_for(self, format: CatalogExportArtifactFormat) -> bytes:
        return {
            CatalogExportArtifactFormat.CANONICAL_JSON: self.canonical_json,
            CatalogExportArtifactFormat.CATALOG_CSV: self.catalog_csv,
            CatalogExportArtifactFormat.MANIFEST_JSON: self.manifest_json,
        }[format]


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogExportResult:
    export_id: UUID
    job_id: UUID
    product_id: UUID
    projection_id: UUID
    projection_product_version: int
    category: ProductCategory
    schema_version: int
    schema_fingerprint: str
    projection_status: CatalogProjectionStatus
    status: CatalogExportStatus
    artifacts: tuple[CatalogExportArtifact, ...]
    warning_reason_codes: tuple[CatalogWarningReason, ...]
    engine: str
    engine_version: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.projection_product_version < 1 or self.schema_version < 1:
            raise ValueError("catalog export versions must be positive")
        if len(self.schema_fingerprint) != 64:
            raise ValueError("catalog export schema fingerprint is invalid")
        if self.projection_status not in {
            CatalogProjectionStatus.READY,
            CatalogProjectionStatus.READY_WITH_WARNINGS,
        }:
            raise ValueError("catalog export projection status is not eligible")
        if self.status is not CatalogExportStatus.EXPORTED:
            raise ValueError("catalog export result status must be EXPORTED")
        if tuple(artifact.format for artifact in self.artifacts) != tuple(
            CatalogExportArtifactFormat
        ):
            raise ValueError("catalog export result requires exactly three ordered artifacts")
        if (
            len({item.file_name for item in self.artifacts}) != 3
            or len({item.object_key for item in self.artifacts}) != 3
        ):
            raise ValueError("catalog export artifact filenames and keys must be unique")
        expected_prefix = f"catalog-exports/{self.export_id}/"
        if any(not item.object_key.startswith(expected_prefix) for item in self.artifacts):
            raise ValueError("catalog export artifact key does not match export identity")
        if len(set(self.warning_reason_codes)) != len(self.warning_reason_codes):
            raise ValueError("catalog export warning codes must be unique")
        if self.projection_status is CatalogProjectionStatus.READY and self.warning_reason_codes:
            raise ValueError("READY export cannot contain warning reasons")
        if (
            self.projection_status is CatalogProjectionStatus.READY_WITH_WARNINGS
            and not self.warning_reason_codes
        ):
            raise ValueError("READY_WITH_WARNINGS export requires warning reasons")
        if self.engine != "deterministic-catalog-exporter-v1" or self.engine_version != "1.0":
            raise ValueError("catalog export engine metadata is invalid")
        object.__setattr__(self, "created_at", _utc(self.created_at))
