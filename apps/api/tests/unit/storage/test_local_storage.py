"""Secure local object-storage behavior tests."""

import hashlib
import io
import json
import os
from pathlib import Path
from typing import BinaryIO

import pytest

from app.core.exceptions import (
    InvalidObjectKeyError,
    ObjectAlreadyExistsError,
    ObjectMetadataError,
    ObjectNotFoundError,
    ObjectSizeExceededError,
    ObjectStorageError,
)
from app.storage.local import LocalObjectStorage

OBJECT_KEY = "products/product-id/sources/source-id/object.pdf"


@pytest.fixture
def storage(tmp_path: Path) -> LocalObjectStorage:
    return LocalObjectStorage(tmp_path / "objects")


def object_path(root: Path) -> Path:
    return root / Path(*OBJECT_KEY.split("/"))


def sidecar_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.metadata.json")


def test_save_streams_bytes_and_returns_known_metadata(
    storage: LocalObjectStorage, tmp_path: Path
) -> None:
    content = b"CatalogIQ storage content"
    stored = storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(content), max_size_bytes=100)
    path = object_path(tmp_path / "objects")

    assert stored.object_key == OBJECT_KEY
    assert stored.size_bytes == len(content)
    assert stored.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert path.read_bytes() == content
    assert sidecar_path(path).is_file()
    assert list(path.parent.glob(".object.tmp-*")) == []


def test_empty_object_is_allowed(storage: LocalObjectStorage) -> None:
    stored = storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(), max_size_bytes=1)
    assert stored.size_bytes == 0
    assert stored.checksum_sha256 == hashlib.sha256(b"").hexdigest()


def test_exact_size_limit_succeeds(storage: LocalObjectStorage) -> None:
    stored = storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"1234"), max_size_bytes=4)
    assert stored.size_bytes == 4


@pytest.mark.parametrize("maximum", [0, -1, True])
def test_non_positive_or_boolean_size_limit_is_rejected(
    storage: LocalObjectStorage, maximum: int
) -> None:
    with pytest.raises(ObjectSizeExceededError):
        storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"x"), max_size_bytes=maximum)


def test_one_byte_over_limit_leaves_no_files(storage: LocalObjectStorage, tmp_path: Path) -> None:
    with pytest.raises(ObjectSizeExceededError):
        storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"12345"), max_size_bytes=4)

    path = object_path(tmp_path / "objects")
    assert not path.exists()
    assert not sidecar_path(path).exists()
    assert list(path.parent.glob(".object.tmp-*")) == []


def test_duplicate_key_does_not_change_existing_object(storage: LocalObjectStorage) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"original"), max_size_bytes=20)

    with pytest.raises(ObjectAlreadyExistsError):
        storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"replacement"), max_size_bytes=20)

    with storage.open(OBJECT_KEY) as stream:
        assert stream.read() == b"original"


class BrokenStream:
    def read(self, size: int = -1) -> bytes:
        del size
        raise OSError("sensitive local stream detail")


def test_stream_failure_is_wrapped_and_temporary_file_removed(
    storage: LocalObjectStorage, tmp_path: Path
) -> None:
    with pytest.raises(ObjectStorageError, match="stream could not be written") as captured:
        storage.save(
            object_key=OBJECT_KEY,
            stream=BrokenStream(),  # type: ignore[arg-type]
            max_size_bytes=10,
        )
    assert "sensitive" not in str(captured.value)
    assert list((tmp_path / "objects").rglob(".object.tmp-*")) == []


def test_non_binary_stream_is_rejected(storage: LocalObjectStorage) -> None:
    with pytest.raises(ObjectStorageError, match="must return bytes"):
        storage.save(  # type: ignore[arg-type]
            object_key=OBJECT_KEY, stream=io.StringIO("text"), max_size_bytes=10
        )


def test_filesystem_temporary_failure_is_wrapped(
    storage: LocalObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_temporary(*args: object, **kwargs: object) -> tuple[int, str]:
        del args, kwargs
        raise OSError("C:/secret/root")

    monkeypatch.setattr("app.storage.local.tempfile.mkstemp", fail_temporary)
    with pytest.raises(
        ObjectStorageError, match="temporary object could not be created"
    ) as captured:
        storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"x"), max_size_bytes=10)
    assert "C:/secret" not in str(captured.value)


def test_file_descriptor_failure_removes_temporary_file(
    storage: LocalObjectStorage, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_fdopen(*args: object, **kwargs: object) -> BinaryIO:
        del args, kwargs
        raise OSError("descriptor failure")

    monkeypatch.setattr("app.storage.local.os.fdopen", fail_fdopen)
    with pytest.raises(ObjectStorageError, match="stream could not be written"):
        storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"x"), max_size_bytes=10)
    assert list((tmp_path / "objects").rglob(".object.tmp-*")) == []


def test_sidecar_finalization_failure_removes_final_object(
    storage: LocalObjectStorage, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_replace = os.replace
    replacements = 0

    def fail_second_replace(source: Path, destination: Path) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("metadata failure")
        real_replace(source, destination)

    monkeypatch.setattr("app.storage.local.os.replace", fail_second_replace)
    with pytest.raises(ObjectStorageError, match="finalized"):
        storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"x"), max_size_bytes=10)

    path = object_path(tmp_path / "objects")
    assert not path.exists()
    assert not sidecar_path(path).exists()
    assert list(path.parent.glob(".object.tmp-*")) == []


def test_save_does_not_create_filesystem_links(
    storage: LocalObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    def reject_link(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("hard-link creation must not be used")

    monkeypatch.setattr("app.storage.local.os.link", reject_link)
    saved = storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    assert saved.size_bytes == 7


def test_open_returns_binary_stream_with_original_bytes(storage: LocalObjectStorage) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    stream: BinaryIO = storage.open(OBJECT_KEY)
    try:
        assert stream.read() == b"content"
    finally:
        stream.close()


def test_missing_open_raises_controlled_error(storage: LocalObjectStorage) -> None:
    with pytest.raises(ObjectNotFoundError):
        storage.open(OBJECT_KEY)


def test_exists_is_true_only_for_regular_objects(
    storage: LocalObjectStorage, tmp_path: Path
) -> None:
    assert storage.exists(OBJECT_KEY) is False
    path = object_path(tmp_path / "objects")
    path.mkdir(parents=True)
    assert storage.exists(OBJECT_KEY) is False
    with pytest.raises(ObjectNotFoundError):
        storage.open(OBJECT_KEY)


def test_unsafe_key_is_rejected_by_every_operation(storage: LocalObjectStorage) -> None:
    with pytest.raises(InvalidObjectKeyError):
        storage.exists("../outside.pdf")
    with pytest.raises(InvalidObjectKeyError):
        storage.open("../outside.pdf")
    with pytest.raises(InvalidObjectKeyError):
        storage.get_metadata("../outside.pdf")
    with pytest.raises(InvalidObjectKeyError):
        storage.delete("../outside.pdf")
    with pytest.raises(InvalidObjectKeyError):
        storage.save(object_key="../outside.pdf", stream=io.BytesIO(), max_size_bytes=1)


def test_metadata_matches_save_result(storage: LocalObjectStorage) -> None:
    saved = storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    assert storage.get_metadata(OBJECT_KEY) == saved


def test_sidecar_cannot_be_opened_as_an_object(storage: LocalObjectStorage) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    with pytest.raises(InvalidObjectKeyError):
        storage.open(f"{OBJECT_KEY}.metadata.json")


def test_missing_sidecar_raises_metadata_error(storage: LocalObjectStorage, tmp_path: Path) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    sidecar_path(object_path(tmp_path / "objects")).unlink()
    with pytest.raises(ObjectMetadataError, match="does not exist"):
        storage.get_metadata(OBJECT_KEY)


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        json.dumps({"objectKey": OBJECT_KEY}),
        json.dumps(
            {
                "objectKey": OBJECT_KEY,
                "sizeBytes": 7,
                "checksumSha256": "not-a-checksum",
                "createdAt": "not-a-date",
            }
        ),
    ],
)
def test_malformed_sidecar_raises_metadata_error(
    storage: LocalObjectStorage, tmp_path: Path, payload: str
) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    sidecar_path(object_path(tmp_path / "objects")).write_text(payload, encoding="utf-8")
    with pytest.raises(ObjectMetadataError):
        storage.get_metadata(OBJECT_KEY)


def test_tampered_object_size_is_detected(storage: LocalObjectStorage, tmp_path: Path) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    object_path(tmp_path / "objects").write_bytes(b"changed-size")
    with pytest.raises(ObjectMetadataError, match="inconsistent"):
        storage.get_metadata(OBJECT_KEY)


def test_delete_removes_object_and_sidecar(storage: LocalObjectStorage, tmp_path: Path) -> None:
    storage.save(object_key=OBJECT_KEY, stream=io.BytesIO(b"content"), max_size_bytes=20)
    path = object_path(tmp_path / "objects")

    storage.delete(OBJECT_KEY)

    assert not path.exists()
    assert not sidecar_path(path).exists()
    assert storage.exists(OBJECT_KEY) is False
    with pytest.raises(ObjectNotFoundError):
        storage.open(OBJECT_KEY)


def test_delete_missing_object_raises_not_found(storage: LocalObjectStorage) -> None:
    with pytest.raises(ObjectNotFoundError):
        storage.delete(OBJECT_KEY)


def test_traversal_never_deletes_outside_file(storage: LocalObjectStorage, tmp_path: Path) -> None:
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"keep")
    with pytest.raises(InvalidObjectKeyError):
        storage.delete("../outside.pdf")
    assert outside.read_bytes() == b"keep"


def test_symlink_object_is_not_exposed(storage: LocalObjectStorage, tmp_path: Path) -> None:
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"outside")
    path = object_path(tmp_path / "objects")
    path.parent.mkdir(parents=True)
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are unavailable")
    with pytest.raises(InvalidObjectKeyError):
        storage.exists(OBJECT_KEY)
    with pytest.raises(InvalidObjectKeyError):
        storage.open(OBJECT_KEY)
