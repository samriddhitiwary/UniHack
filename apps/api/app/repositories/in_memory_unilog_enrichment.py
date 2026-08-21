"""Idempotent in-memory challenge enrichment result repository."""

from app.domain.unilog_challenge import UnilogEnrichmentResult


class InMemoryUnilogEnrichmentRepository:
    def __init__(self) -> None:
        self._items: dict[str, UnilogEnrichmentResult] = {}

    def save(self, result: UnilogEnrichmentResult) -> None:
        current = self._items.get(result.enrichment_id)
        if current is not None and current.input_row_id != result.input_row_id:
            raise ValueError("enrichment identity collision")
        self._items[result.enrichment_id] = result

    def get(self, enrichment_id: str) -> UnilogEnrichmentResult | None:
        return self._items.get(enrichment_id)
