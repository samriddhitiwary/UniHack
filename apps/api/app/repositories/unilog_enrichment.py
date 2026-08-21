"""Persistence boundary for isolated challenge enrichment results."""

from typing import Protocol

from app.domain.unilog_challenge import UnilogEnrichmentResult


class UnilogEnrichmentRepository(Protocol):
    def save(self, result: UnilogEnrichmentResult) -> None: ...

    def get(self, enrichment_id: str) -> UnilogEnrichmentResult | None: ...
