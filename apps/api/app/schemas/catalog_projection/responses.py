"""Public read models for immutable commerce catalog projections."""

from app.schemas.catalog_projection.models import CommerceCatalogProjectionRecord


class CatalogProjectionResponse(CommerceCatalogProjectionRecord):
    """The compact SPEC-031 projection exposed without raw upstream evidence."""
