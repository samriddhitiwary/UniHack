"""Catalog export result and artifact enumerations."""

from enum import StrEnum


class CatalogExportArtifactFormat(StrEnum):
    CANONICAL_JSON = "CANONICAL_JSON"
    CATALOG_CSV = "CATALOG_CSV"
    MANIFEST_JSON = "MANIFEST_JSON"


class CatalogExportStatus(StrEnum):
    EXPORTED = "EXPORTED"
