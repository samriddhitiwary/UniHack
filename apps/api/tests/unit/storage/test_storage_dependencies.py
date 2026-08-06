"""Object-storage configuration and provider tests."""

import io
from pathlib import Path
from typing import BinaryIO

import pytest

from app.core.config import Settings
from app.core.exceptions import ObjectStorageConfigurationError
from app.storage.dependencies import create_object_storage, get_object_storage
from app.storage.local import LocalObjectStorage
from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage


def test_local_backend_creates_and_uses_configured_root(tmp_path: Path) -> None:
    root = tmp_path / "configured" / "objects"
    storage = create_object_storage(Settings(storage_backend="local", local_storage_root=root))
    assert isinstance(storage, LocalObjectStorage)
    assert root.is_dir()
    storage.save(
        object_key="products/product/sources/source/object.pdf",
        stream=io.BytesIO(b"content"),
        max_size_bytes=20,
    )
    assert (root / "products/product/sources/source/object.pdf").is_file()


def test_default_local_root_configuration_is_available() -> None:
    assert Settings().local_storage_root == Path("../../storage")


def test_root_pointing_to_file_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "not-a-directory"
    root.write_text("file", encoding="utf-8")
    with pytest.raises(ObjectStorageConfigurationError, match="directory"):
        create_object_storage(Settings(local_storage_root=root))


def test_unsupported_reserved_backend_is_rejected(tmp_path: Path) -> None:
    settings = Settings(storage_backend="s3", local_storage_root=tmp_path)
    with pytest.raises(ObjectStorageConfigurationError, match="unsupported"):
        create_object_storage(settings)


def test_cached_dependency_is_reusable_and_clearable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(local_storage_root=tmp_path / "cached")
    monkeypatch.setattr("app.storage.dependencies.get_settings", lambda: settings)
    get_object_storage.cache_clear()
    try:
        first = get_object_storage()
        assert first is get_object_storage()
    finally:
        get_object_storage.cache_clear()


def test_protocol_is_easy_to_replace_with_a_fake() -> None:
    class FakeStorage:
        def save(self, *, object_key: str, stream: BinaryIO, max_size_bytes: int) -> StoredObject:
            raise NotImplementedError

        def open(self, object_key: str) -> BinaryIO:
            raise NotImplementedError

        def exists(self, object_key: str) -> bool:
            return False

        def get_metadata(self, object_key: str) -> StoredObject:
            raise NotImplementedError

        def delete(self, object_key: str) -> None:
            return None

    def accepts_storage(storage: ObjectStorage) -> bool:
        return storage.exists("products/product/sources/source/object.pdf")

    fake = FakeStorage()
    assert accepts_storage(fake) is False
