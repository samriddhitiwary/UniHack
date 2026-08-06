"""Object-key generation and validation tests."""

from pathlib import PurePosixPath
from uuid import uuid4

import pytest

from app.core.exceptions import InvalidObjectKeyError, UnsupportedObjectExtensionError
from app.storage.keys import generate_object_key, validate_object_key


@pytest.mark.parametrize("extension", ["pdf", "png", "jpg", "jpeg", "webp", "csv"])
def test_generated_key_uses_ids_random_name_and_normalized_extension(extension: str) -> None:
    product_id = uuid4()
    source_id = uuid4()
    original = f"Customer File.{extension.upper()}"

    key = generate_object_key(
        product_id=product_id,
        source_id=source_id,
        original_filename=original,
    )

    assert key.startswith(f"products/{product_id}/sources/{source_id}/")
    assert key.endswith(f".{extension}")
    assert "Customer File" not in key
    assert "\\" not in key
    assert len(PurePosixPath(key).stem) == 36


def test_generated_keys_are_unique() -> None:
    product_id = uuid4()
    source_id = uuid4()
    keys = {
        generate_object_key(
            product_id=product_id,
            source_id=source_id,
            original_filename="source.pdf",
        )
        for _ in range(10)
    }
    assert len(keys) == 10


@pytest.mark.parametrize("filename", ["", "   ", "source.exe", "source", "folder/file.pdf"])
def test_missing_or_unsupported_extension_is_rejected(filename: str) -> None:
    with pytest.raises(UnsupportedObjectExtensionError):
        generate_object_key(product_id=uuid4(), source_id=uuid4(), original_filename=filename)


def test_generator_requires_uuid_namespaces() -> None:
    with pytest.raises(InvalidObjectKeyError):
        generate_object_key(  # type: ignore[arg-type]
            product_id="product", source_id=uuid4(), original_filename="source.pdf"
        )


@pytest.mark.parametrize(
    "key",
    [
        "../file.pdf",
        "products/../../file.pdf",
        "/file.pdf",
        "\\file.pdf",
        "C:\\file.pdf",
        "C:/file.pdf",
        "file://path/file.pdf",
        "products\\id\\file.pdf",
        "products/id/\x00file.pdf",
        "",
        "   ",
        "products//file.pdf",
        "products/./file.pdf",
        "products/file.pdf/",
        " products/file.pdf",
        "products/file.pdf ",
        "products/file.pdf.metadata.json",
        "products/.object.tmp-value",
    ],
)
def test_unsafe_keys_are_rejected(key: str) -> None:
    with pytest.raises(InvalidObjectKeyError):
        validate_object_key(key)


def test_valid_nested_key_is_returned() -> None:
    key = "products/abc-123/sources/def-456/object.pdf"
    assert validate_object_key(key) == key


def test_maximum_key_length_is_accepted() -> None:
    key = "/".join(["a" * 255, "b" * 255, "c" * 255, "d" * 254, "e"])
    assert len(key) == 1_024
    assert validate_object_key(key) == key


def test_excessive_key_length_is_rejected() -> None:
    key = "/".join(["a" * 255, "b" * 255, "c" * 255, "d" * 255, "e"])
    assert len(key) == 1_025
    with pytest.raises(InvalidObjectKeyError):
        validate_object_key(key)
