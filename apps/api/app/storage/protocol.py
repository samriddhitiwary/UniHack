"""Object-storage contract used by future application services."""

from typing import BinaryIO, Protocol

from app.storage.models import StoredObject


class ObjectStorage(Protocol):
    """Provider-independent binary object operations."""

    def save(self, *, object_key: str, stream: BinaryIO, max_size_bytes: int) -> StoredObject: ...

    def open(self, object_key: str) -> BinaryIO: ...

    def exists(self, object_key: str) -> bool: ...

    def get_metadata(self, object_key: str) -> StoredObject: ...

    def delete(self, object_key: str) -> None: ...
