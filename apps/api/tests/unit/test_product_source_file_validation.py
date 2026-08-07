"""Product-source upload validation tests."""

import io

import pytest

from app.core.exceptions import (
    InvalidProductSourceFileContentError,
    InvalidProductSourceFilenameError,
    ProductSourceMimeTypeMismatchError,
    UnsupportedProductSourceFileTypeError,
)
from app.utils.file_validation import UploadSizeLimits, validate_upload

LIMITS = UploadSizeLimits(pdf=10, image=20, csv=30)


@pytest.mark.parametrize("filename", [None, "", "   ", "bad\x00.pdf", "x" * 256 + ".pdf"])
def test_invalid_filename_is_rejected(filename: str | None) -> None:
    with pytest.raises(InvalidProductSourceFilenameError):
        validate_upload(
            stream=io.BytesIO(b"%PDF-x"),
            original_filename=filename,
            declared_mime_type="application/pdf",
            limits=LIMITS,
        )


def test_fake_path_is_reduced_and_extension_normalized() -> None:
    result = validate_upload(
        stream=io.BytesIO(b"%PDF-x"),
        original_filename=r"C:\fakepath\Pump.PDF",
        declared_mime_type=" Application/PDF; charset=binary",
        limits=LIMITS,
    )
    assert result.original_filename == "Pump.pdf"
    assert result.max_size_bytes == 10
    assert result.stream.read() == b"%PDF-x"


def test_unsupported_extension_and_mime_mismatch_are_distinct() -> None:
    with pytest.raises(UnsupportedProductSourceFileTypeError):
        validate_upload(
            stream=io.BytesIO(b"x"),
            original_filename="x.exe",
            declared_mime_type="application/octet-stream",
            limits=LIMITS,
        )
    with pytest.raises(ProductSourceMimeTypeMismatchError):
        validate_upload(
            stream=io.BytesIO(b"%PDF-x"),
            original_filename="x.pdf",
            declared_mime_type="image/png",
            limits=LIMITS,
        )


@pytest.mark.parametrize(
    ("filename", "mime", "content"),
    [
        ("x.pdf", "application/pdf", b"text"),
        ("x.png", "image/png", b"bad"),
        ("x.jpg", "image/jpeg", b"bad"),
        ("x.webp", "image/webp", b"RIFFbad"),
        ("x.csv", "text/csv", b""),
        ("x.csv", "text/csv", b"a\x00b"),
        ("x.csv", "text/csv", b"\xff"),
    ],
)
def test_invalid_content_is_rejected(filename: str, mime: str, content: bytes) -> None:
    with pytest.raises(InvalidProductSourceFileContentError):
        validate_upload(
            stream=io.BytesIO(content),
            original_filename=filename,
            declared_mime_type=mime,
            limits=LIMITS,
        )


class NonSeekable:
    def __init__(self, data: bytes) -> None:
        self._stream = io.BytesIO(data)

    def seekable(self) -> bool:
        return False

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


def test_nonseekable_stream_replays_inspected_bytes() -> None:
    content = b"%PDF-" + b"x" * 5000
    result = validate_upload(
        stream=NonSeekable(content),
        original_filename="x.pdf",
        declared_mime_type="application/pdf",
        limits=LIMITS,
    )  # type: ignore[arg-type]
    assert result.stream.read() == content


def test_limits_must_be_positive() -> None:
    with pytest.raises(ValueError):
        UploadSizeLimits(pdf=0, image=1, csv=1)
