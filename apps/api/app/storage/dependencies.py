"""Configuration-driven object-storage construction."""

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.core.exceptions import ObjectStorageConfigurationError
from app.storage.local import LocalObjectStorage
from app.storage.protocol import ObjectStorage


def create_object_storage(settings: Settings) -> ObjectStorage:
    """Build the selected backend without silently falling back."""
    if settings.storage_backend == "local":
        return LocalObjectStorage(settings.local_storage_path())
    raise ObjectStorageConfigurationError("configured object-storage backend is unsupported")


@lru_cache
def get_object_storage() -> ObjectStorage:
    """Return one reusable configured storage dependency."""
    return create_object_storage(get_settings())
