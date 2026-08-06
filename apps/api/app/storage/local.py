"""Secure local-filesystem implementation of the object-storage contract."""

import hashlib
import json
import logging
import os
import tempfile
from collections.abc import Mapping
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import (
    InvalidObjectKeyError,
    ObjectAlreadyExistsError,
    ObjectMetadataError,
    ObjectNotFoundError,
    ObjectSizeExceededError,
    ObjectStorageConfigurationError,
    ObjectStorageError,
)
from app.storage.keys import METADATA_SUFFIX, validate_object_key
from app.storage.models import StoredObject

logger = logging.getLogger(__name__)

STREAM_CHUNK_SIZE = 256 * 1024
_METADATA_FIELDS = frozenset({"objectKey", "sizeBytes", "checksumSha256", "createdAt"})


class LocalObjectStorage:
    """Store objects under one resolved development-only filesystem root."""

    def __init__(self, root: Path) -> None:
        try:
            candidate = root.expanduser()
            if candidate.exists() and not candidate.is_dir():
                raise ObjectStorageConfigurationError("local storage root must be a directory")
            candidate.mkdir(parents=True, exist_ok=True)
            self._root = candidate.resolve(strict=True)
            if not self._root.is_dir():
                raise ObjectStorageConfigurationError("local storage root must be a directory")
        except ObjectStorageConfigurationError:
            raise
        except (OSError, RuntimeError) as exc:
            raise ObjectStorageConfigurationError("local storage root is unavailable") from exc

    def save(self, *, object_key: str, stream: BinaryIO, max_size_bytes: int) -> StoredObject:
        """Stream an object to temporary files and finalize it without overwrite."""
        if isinstance(max_size_bytes, bool) or not isinstance(max_size_bytes, int):
            raise ObjectSizeExceededError("maximum object size must be a positive integer")
        if max_size_bytes <= 0:
            raise ObjectSizeExceededError("maximum object size must be positive")

        destination = self._object_path(object_key)
        sidecar = self._metadata_path(destination)
        category = self._key_category(object_key)
        logger.info("event=object_storage.save_started backend=local category=%s", category)

        data_temporary: Path | None = None
        metadata_temporary: Path | None = None
        object_finalized = False
        metadata_finalized = False
        try:
            self._prepare_parent(destination)
            if self._path_exists(destination) or self._path_exists(sidecar):
                raise ObjectAlreadyExistsError("object key already exists")

            data_temporary, total, checksum = self._write_stream(
                destination.parent, stream, max_size_bytes
            )
            stored = StoredObject(
                object_key=object_key,
                size_bytes=total,
                checksum_sha256=checksum,
                created_at=datetime.now(UTC),
            )
            metadata_temporary = self._write_metadata_temporary(destination.parent, stored)

            self._link_exclusive(data_temporary, destination)
            object_finalized = True
            self._link_exclusive(metadata_temporary, sidecar)
            metadata_finalized = True
        except ObjectStorageError:
            if metadata_finalized:
                self._safe_unlink(sidecar)
            if object_finalized:
                self._safe_unlink(destination)
            logger.warning("event=object_storage.failed backend=local category=%s", category)
            raise
        except Exception as exc:
            if metadata_finalized:
                self._safe_unlink(sidecar)
            if object_finalized:
                self._safe_unlink(destination)
            logger.warning("event=object_storage.failed backend=local category=%s", category)
            raise ObjectStorageError("object could not be saved") from exc
        finally:
            self._safe_unlink(data_temporary)
            self._safe_unlink(metadata_temporary)

        logger.info(
            "event=object_storage.saved backend=local category=%s size_bytes=%s checksum_prefix=%s",
            category,
            stored.size_bytes,
            stored.checksum_sha256[:12],
        )
        return stored

    def open(self, object_key: str) -> BinaryIO:
        """Open one regular, non-link object for binary streaming reads."""
        path = self._existing_object_path(object_key)
        try:
            stream = path.open("rb")
        except FileNotFoundError as exc:
            raise ObjectNotFoundError("object does not exist") from exc
        except OSError as exc:
            raise ObjectStorageError("object could not be opened") from exc
        logger.info(
            "event=object_storage.opened backend=local category=%s",
            self._key_category(object_key),
        )
        return stream

    def exists(self, object_key: str) -> bool:
        """Return whether a key identifies an existing regular, non-link file."""
        path = self._object_path(object_key)
        try:
            return path.is_file() and not path.is_symlink()
        except OSError as exc:
            raise ObjectStorageError("object existence could not be checked") from exc

    def get_metadata(self, object_key: str) -> StoredObject:
        """Load and validate the object's strict JSON sidecar."""
        path = self._existing_object_path(object_key)
        sidecar = self._metadata_path(path)
        if not sidecar.is_file() or sidecar.is_symlink():
            raise ObjectMetadataError("object metadata does not exist")
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            stored = self._parse_metadata(payload)
            if stored.object_key != object_key or stored.size_bytes != path.stat().st_size:
                raise ObjectMetadataError("object metadata is inconsistent")
            return stored
        except ObjectMetadataError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ObjectMetadataError("object metadata is invalid") from exc

    def delete(self, object_key: str) -> None:
        """Delete one object and its sidecar without cascading to other keys."""
        path = self._existing_object_path(object_key)
        sidecar = self._metadata_path(path)
        try:
            path.unlink()
            if self._path_exists(sidecar):
                sidecar.unlink()
        except FileNotFoundError as exc:
            raise ObjectNotFoundError("object does not exist") from exc
        except OSError as exc:
            raise ObjectStorageError("object could not be deleted") from exc
        logger.info(
            "event=object_storage.deleted backend=local category=%s",
            self._key_category(object_key),
        )

    def _object_path(self, object_key: str) -> Path:
        validate_object_key(object_key)
        try:
            path = self._root / Path(*object_key.split("/"))
            resolved = path.resolve(strict=False)
            resolved.relative_to(self._root)
            current = self._root
            for segment in object_key.split("/")[:-1]:
                current /= segment
                if current.is_symlink():
                    raise InvalidObjectKeyError("object key traverses a symbolic link")
        except InvalidObjectKeyError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise InvalidObjectKeyError("object key escapes the storage root") from exc
        return path

    def _existing_object_path(self, object_key: str) -> Path:
        path = self._object_path(object_key)
        try:
            if not path.is_file() or path.is_symlink():
                raise ObjectNotFoundError("object does not exist")
        except OSError as exc:
            raise ObjectStorageError("object could not be inspected") from exc
        return path

    def _prepare_parent(self, destination: Path) -> None:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            resolved_parent = destination.parent.resolve(strict=True)
            resolved_parent.relative_to(self._root)
            if not resolved_parent.is_dir():
                raise ObjectStorageError("object parent is unavailable")
        except ObjectStorageError:
            raise
        except (OSError, RuntimeError, ValueError) as exc:
            raise ObjectStorageError("object parent could not be prepared") from exc

    def _write_stream(
        self, parent: Path, stream: BinaryIO, max_size_bytes: int
    ) -> tuple[Path, int, str]:
        descriptor, temporary_name = self._create_temporary(parent)
        temporary = Path(temporary_name)
        descriptor_owned = True
        total = 0
        digest = hashlib.sha256()
        try:
            output = os.fdopen(descriptor, "wb")
            descriptor_owned = False
            with output:
                while True:
                    chunk = stream.read(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    if not isinstance(chunk, bytes):
                        raise ObjectStorageError("object stream must return bytes")
                    total += len(chunk)
                    if total > max_size_bytes:
                        raise ObjectSizeExceededError("object exceeds the maximum permitted size")
                    written = output.write(chunk)
                    if written != len(chunk):
                        raise OSError("incomplete object write")
                    digest.update(chunk)
                output.flush()
        except ObjectStorageError:
            if descriptor_owned:
                self._safe_close(descriptor)
            self._safe_unlink(temporary)
            raise
        except Exception as exc:
            if descriptor_owned:
                self._safe_close(descriptor)
            self._safe_unlink(temporary)
            raise ObjectStorageError("object stream could not be written") from exc
        return temporary, total, digest.hexdigest()

    def _write_metadata_temporary(self, parent: Path, stored: StoredObject) -> Path:
        descriptor, temporary_name = self._create_temporary(parent)
        temporary = Path(temporary_name)
        descriptor_owned = True
        payload = {
            "objectKey": stored.object_key,
            "sizeBytes": stored.size_bytes,
            "checksumSha256": stored.checksum_sha256,
            "createdAt": stored.created_at.isoformat().replace("+00:00", "Z"),
        }
        try:
            output = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
            descriptor_owned = False
            with output:
                json.dump(payload, output, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
                output.write("\n")
                output.flush()
        except Exception as exc:
            if descriptor_owned:
                self._safe_close(descriptor)
            self._safe_unlink(temporary)
            raise ObjectStorageError("object metadata could not be written") from exc
        return temporary

    @staticmethod
    def _parse_metadata(payload: object) -> StoredObject:
        if not isinstance(payload, Mapping) or set(payload) != _METADATA_FIELDS:
            raise ObjectMetadataError("object metadata is invalid")
        object_key = payload["objectKey"]
        size_bytes = payload["sizeBytes"]
        checksum = payload["checksumSha256"]
        created_at = payload["createdAt"]
        if (
            not isinstance(object_key, str)
            or isinstance(size_bytes, bool)
            or not isinstance(size_bytes, int)
            or not isinstance(checksum, str)
            or not isinstance(created_at, str)
        ):
            raise ObjectMetadataError("object metadata is invalid")
        try:
            timestamp = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            return StoredObject(
                object_key=object_key,
                size_bytes=size_bytes,
                checksum_sha256=checksum,
                created_at=timestamp,
            )
        except (InvalidObjectKeyError, ValueError) as exc:
            raise ObjectMetadataError("object metadata is invalid") from exc

    @staticmethod
    def _create_temporary(parent: Path) -> tuple[int, str]:
        try:
            return tempfile.mkstemp(prefix=".object.tmp-", dir=parent)
        except OSError as exc:
            raise ObjectStorageError("temporary object could not be created") from exc

    @staticmethod
    def _link_exclusive(source: Path, destination: Path) -> None:
        try:
            os.link(source, destination)
        except FileExistsError as exc:
            raise ObjectAlreadyExistsError("object key already exists") from exc
        except OSError as exc:
            raise ObjectStorageError("object could not be finalized") from exc

    @staticmethod
    def _metadata_path(destination: Path) -> Path:
        return destination.with_name(f"{destination.name}{METADATA_SUFFIX}")

    @staticmethod
    def _path_exists(path: Path) -> bool:
        return os.path.lexists(path)

    @staticmethod
    def _safe_unlink(path: Path | None) -> None:
        if path is None:
            return
        with suppress(OSError):
            path.unlink(missing_ok=True)

    @staticmethod
    def _safe_close(descriptor: int) -> None:
        with suppress(OSError):
            os.close(descriptor)

    @staticmethod
    def _key_category(object_key: str) -> str:
        try:
            return validate_object_key(object_key).split("/", maxsplit=1)[0]
        except InvalidObjectKeyError:
            return "invalid"
