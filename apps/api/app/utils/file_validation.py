"""Bounded, transport-neutral product-source upload validation."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import BinaryIO, cast

from app.core.exceptions import (
    InvalidProductSourceFileContentError,
    InvalidProductSourceFilenameError,
    ProductSourceMimeTypeMismatchError,
    UnsupportedProductSourceFileTypeError,
)
from app.domain.product_sources import ProductSourceType
from app.domain.product_sources.entities import ORIGINAL_FILENAME_MAX_LENGTH

INSPECTION_BYTES = 4096


@dataclass(frozen=True, slots=True)
class UploadSizeLimits:
    pdf: int
    image: int
    csv: int

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in (self.pdf, self.image, self.csv)
        ):
            raise ValueError("upload size limits must be positive integers")

    def for_type(self, source_type: ProductSourceType) -> int:
        return {
            ProductSourceType.PDF: self.pdf,
            ProductSourceType.IMAGE: self.image,
            ProductSourceType.CSV: self.csv,
        }[source_type]


@dataclass(frozen=True, slots=True)
class UploadType:
    source_type: ProductSourceType
    mime_types: frozenset[str]


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    stream: BinaryIO
    original_filename: str
    extension: str
    mime_type: str
    source_type: ProductSourceType
    max_size_bytes: int


UPLOAD_TYPES = {
    ".pdf": UploadType(ProductSourceType.PDF, frozenset({"application/pdf"})),
    ".png": UploadType(ProductSourceType.IMAGE, frozenset({"image/png"})),
    ".jpg": UploadType(ProductSourceType.IMAGE, frozenset({"image/jpeg"})),
    ".jpeg": UploadType(ProductSourceType.IMAGE, frozenset({"image/jpeg"})),
    ".webp": UploadType(ProductSourceType.IMAGE, frozenset({"image/webp"})),
    ".csv": UploadType(
        ProductSourceType.CSV,
        frozenset({"text/csv", "application/csv", "application/vnd.ms-excel"}),
    ),
}


class _PrefixedStream:
    def __init__(self, prefix: bytes, stream: BinaryIO) -> None:
        self._prefix = prefix
        self._stream = stream

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            result = self._prefix + self._stream.read()
            self._prefix = b""
            return result
        prefix = self._prefix[:size]
        self._prefix = self._prefix[size:]
        remainder = self._stream.read(size - len(prefix)) if len(prefix) < size else b""
        return prefix + remainder


def validate_upload(
    *,
    stream: BinaryIO,
    original_filename: str | None,
    declared_mime_type: str | None,
    limits: UploadSizeLimits,
) -> ValidatedUpload:
    filename, extension, upload_type = _validate_filename(original_filename)
    mime_type = _validate_mime(declared_mime_type, upload_type)
    inspected_stream, sample = _inspect(stream)
    _validate_content(extension, sample)
    return ValidatedUpload(
        stream=inspected_stream,
        original_filename=filename,
        extension=extension,
        mime_type=mime_type,
        source_type=upload_type.source_type,
        max_size_bytes=limits.for_type(upload_type.source_type),
    )


def _validate_filename(filename: str | None) -> tuple[str, str, UploadType]:
    if filename is None or "\x00" in filename:
        raise InvalidProductSourceFilenameError("upload filename is invalid")
    basename = filename.strip().replace("\\", "/").rsplit("/", maxsplit=1)[-1].strip()
    if not basename or len(basename) > ORIGINAL_FILENAME_MAX_LENGTH:
        raise InvalidProductSourceFilenameError("upload filename is invalid")
    extension = PurePosixPath(basename).suffix.lower()
    upload_type = UPLOAD_TYPES.get(extension)
    if upload_type is None:
        raise UnsupportedProductSourceFileTypeError("product source file type is unsupported")
    normalized = f"{basename[: -len(extension)]}{extension}"
    return normalized, extension, upload_type


def _validate_mime(mime_type: str | None, upload_type: UploadType) -> str:
    normalized = (mime_type or "").split(";", maxsplit=1)[0].strip().lower()
    if normalized not in upload_type.mime_types:
        raise ProductSourceMimeTypeMismatchError("declared MIME type does not match file type")
    return normalized


def _inspect(stream: BinaryIO) -> tuple[BinaryIO, bytes]:
    position: int | None = None
    try:
        if stream.seekable():
            position = stream.tell()
    except (AttributeError, OSError):
        position = None
    try:
        sample = stream.read(INSPECTION_BYTES)
    except Exception as exc:
        raise InvalidProductSourceFileContentError("file content could not be inspected") from exc
    if not isinstance(sample, bytes):
        raise InvalidProductSourceFileContentError("file stream must contain bytes")
    if position is not None:
        try:
            stream.seek(position)
            return stream, sample
        except OSError as exc:
            raise InvalidProductSourceFileContentError("file stream could not be restored") from exc
    return cast(BinaryIO, _PrefixedStream(sample, stream)), sample


def _validate_content(extension: str, sample: bytes) -> None:
    valid = False
    if extension == ".pdf":
        valid = sample.startswith(b"%PDF-")
    elif extension == ".png":
        valid = sample.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in {".jpg", ".jpeg"}:
        valid = sample.startswith(b"\xff\xd8\xff")
    elif extension == ".webp":
        valid = len(sample) >= 12 and sample[:4] == b"RIFF" and sample[8:12] == b"WEBP"
    elif extension == ".csv":
        valid = _valid_csv_sample(sample)
    if not valid:
        raise InvalidProductSourceFileContentError("file content does not match its type")


def _valid_csv_sample(sample: bytes) -> bool:
    if not sample or b"\x00" in sample:
        return False
    try:
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return not any(ord(character) < 32 and character not in "\t\r\n" for character in text)
