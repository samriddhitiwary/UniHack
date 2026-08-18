"""Catalog export domain invariant tests."""

from dataclasses import FrozenInstanceError, replace

import pytest

from app.domain.catalog_export import (
    CatalogExportArtifactFormat,
    CatalogExportStatus,
)
from app.domain.catalog_projection import CatalogProjectionStatus
from tests.fixtures.catalog_export import export_result


def test_export_result_and_artifacts_are_immutable_and_coherent() -> None:
    _, _, _, result = export_result()
    assert result.status is CatalogExportStatus.EXPORTED
    assert len(result.artifacts) == 3
    with pytest.raises(FrozenInstanceError):
        result.status = CatalogExportStatus.EXPORTED  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.artifacts[0].size_bytes = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    "changes",
    [
        {"size_bytes": 0},
        {"sha256": "A" * 64},
        {"sha256": "x" * 64},
        {"file_name": "product-name.json"},
        {"object_key": "../catalog.json"},
    ],
)
def test_artifact_rejects_invalid_size_hash_name_or_key(changes: dict[str, object]) -> None:
    _, _, _, result = export_result()
    with pytest.raises(ValueError):
        replace(result.artifacts[0], **changes)


def test_result_requires_exact_ordered_formats_unique_keys_and_eligible_status() -> None:
    _, _, _, result = export_result()
    with pytest.raises(ValueError):
        replace(result, artifacts=result.artifacts[:2])
    with pytest.raises(ValueError):
        replace(
            result,
            artifacts=(result.artifacts[0], result.artifacts[0], result.artifacts[2]),
        )
    with pytest.raises(ValueError):
        replace(result, projection_status=CatalogProjectionStatus.BLOCKED)


def test_artifact_format_contract_is_exact() -> None:
    assert [item.value for item in CatalogExportArtifactFormat] == [
        "CANONICAL_JSON",
        "CATALOG_CSV",
        "MANIFEST_JSON",
    ]
