"""Provider-independent object storage contracts and implementations."""

from app.storage.models import StoredObject
from app.storage.protocol import ObjectStorage

__all__ = ["ObjectStorage", "StoredObject"]
