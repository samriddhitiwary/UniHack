"""Catalog export package contract against isolated LocalObjectStorage."""

import hashlib
import io
from pathlib import Path

from app.storage.local import LocalObjectStorage
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_export import EXPORT_ID, export_result, package_builder


def test_three_export_files_round_trip_through_local_object_storage(tmp_path: Path) -> None:
    _, projection, _, _ = export_result()
    package = package_builder().build(export_id=EXPORT_ID, projection=projection, created_at=NOW)
    storage = LocalObjectStorage(tmp_path / "exports")
    try:
        for artifact in package.artifacts:
            content = package.content_for(artifact.format)
            stored = storage.save(
                object_key=artifact.object_key,
                stream=io.BytesIO(content),
                max_size_bytes=len(content),
            )
            assert stored.size_bytes == len(content)
            assert stored.checksum_sha256 == hashlib.sha256(content).hexdigest()
            with storage.open(artifact.object_key) as stream:
                assert stream.read() == content
    finally:
        for artifact in package.artifacts:
            if storage.exists(artifact.object_key):
                storage.delete(artifact.object_key)
