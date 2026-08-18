"""Bounded deterministic catalog export package tests."""

import hashlib

import pytest

from app.core.exceptions import (
    CatalogExportAttributeLimitExceededError,
    CatalogExportCsvSizeLimitExceededError,
    CatalogExportJsonSizeLimitExceededError,
    CatalogExportManifestSizeLimitExceededError,
)
from app.domain.catalog_export import CatalogExportArtifactFormat
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_export import EXPORT_ID, export_result, package_builder


def test_package_contains_exact_three_fixed_safe_artifacts_with_exact_checksums() -> None:
    _, projection, _, _ = export_result()
    package = package_builder().build(export_id=EXPORT_ID, projection=projection, created_at=NOW)
    assert tuple(item.format for item in package.artifacts) == tuple(CatalogExportArtifactFormat)
    assert tuple(item.file_name for item in package.artifacts) == (
        "catalog.json",
        "catalog.csv",
        "manifest.json",
    )
    for artifact in package.artifacts:
        content = package.content_for(artifact.format)
        assert artifact.object_key == f"catalog-exports/{EXPORT_ID}/{artifact.file_name}"
        assert artifact.size_bytes == len(content)
        assert artifact.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    ("builder", "error"),
    [
        (package_builder(json_limit=1), CatalogExportJsonSizeLimitExceededError),
        (package_builder(csv_limit=1), CatalogExportCsvSizeLimitExceededError),
        (package_builder(manifest_limit=1), CatalogExportManifestSizeLimitExceededError),
        (package_builder(attributes=1), CatalogExportAttributeLimitExceededError),
    ],
)
def test_package_enforces_independent_limits(builder, error: type[Exception]) -> None:
    _, projection, _, _ = export_result()
    with pytest.raises(error):
        builder.build(export_id=EXPORT_ID, projection=projection, created_at=NOW)
