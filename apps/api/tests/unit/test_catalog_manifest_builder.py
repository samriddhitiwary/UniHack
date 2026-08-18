"""Publication manifest serializer tests."""

import json

from app.domain.catalog_export import CatalogExportArtifactFormat
from app.services.catalog_manifest_builder import CatalogManifestBuilder
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_export import EXPORT_ID, export_result


def test_manifest_is_deterministic_and_lists_json_csv_without_self_hash() -> None:
    _, projection, package, _ = export_result(manufacturer=None)
    builder = CatalogManifestBuilder()
    args = {
        "export_id": EXPORT_ID,
        "projection": projection,
        "artifacts_without_manifest": package.artifacts[:2],
        "created_at": NOW,
    }
    first = builder.build(**args)
    assert first == builder.build(**args)
    body = json.loads(first)
    assert body["packageVersion"] == 1
    assert body["exportId"] == str(EXPORT_ID)
    assert [item["format"] for item in body["artifacts"]] == [
        CatalogExportArtifactFormat.CANONICAL_JSON.value,
        CatalogExportArtifactFormat.CATALOG_CSV.value,
    ]
    assert "MANIFEST_JSON" not in first.decode()
    assert body["warningReasonCodes"] == ["MANUFACTURER_MISSING"]


def test_manifest_artifact_sizes_and_hashes_match_package_metadata() -> None:
    _, _, package, _ = export_result()
    body = json.loads(package.manifest_json)
    for serialized, artifact in zip(body["artifacts"], package.artifacts[:2], strict=True):
        assert serialized["fileName"] == artifact.file_name
        assert serialized["sizeBytes"] == artifact.size_bytes
        assert serialized["sha256"] == artifact.sha256
