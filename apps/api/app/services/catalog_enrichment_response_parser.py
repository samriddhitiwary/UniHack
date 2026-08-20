"""Strict bounded parser for provider-generated catalog content."""

import json
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import (
    CatalogEnrichmentOutputLimitError,
    CatalogEnrichmentResponseInvalidError,
)
from app.domain.catalog_enrichment import GroundedGeneratedText

_ROOT_KEYS = {"title", "description", "featureBullets", "searchKeywords", "technicalSummary"}
_ITEM_KEYS = {"text", "factIds"}


@dataclass(frozen=True, slots=True, kw_only=True)
class ParsedCatalogEnrichment:
    title: GroundedGeneratedText
    description: GroundedGeneratedText
    feature_bullets: tuple[GroundedGeneratedText, ...]
    search_keywords: tuple[GroundedGeneratedText, ...]
    technical_summary: GroundedGeneratedText

    def all_items(self) -> tuple[GroundedGeneratedText, ...]:
        return (
            self.title,
            self.description,
            *self.feature_bullets,
            *self.search_keywords,
            self.technical_summary,
        )


class CatalogEnrichmentResponseParser:
    def __init__(
        self,
        *,
        max_title: int,
        max_description: int,
        max_bullets: int,
        max_bullet: int,
        max_keywords: int,
        max_keyword: int,
        max_summary: int,
        max_refs_per_item: int,
        max_total_refs: int,
    ) -> None:
        self._limits = (max_title, max_description, max_bullet, max_keyword, max_summary)
        self._max_bullets = max_bullets
        self._max_keywords = max_keywords
        self._max_refs = max_refs_per_item
        self._max_total_refs = max_total_refs

    def parse(self, raw: str) -> ParsedCatalogEnrichment:
        try:
            data = json.loads(raw)
            if not isinstance(data, dict) or set(data) != _ROOT_KEYS:
                raise CatalogEnrichmentResponseInvalidError()
            title = self._item(data["title"], self._limits[0])
            description = self._item(data["description"], self._limits[1])
            summary = self._item(data["technicalSummary"], self._limits[4])
            bullets = self._items(data["featureBullets"], self._limits[2])
            keywords = self._items(data["searchKeywords"], self._limits[3])
            if not 3 <= len(bullets) <= self._max_bullets:
                raise CatalogEnrichmentOutputLimitError()
            if not 1 <= len(keywords) <= self._max_keywords:
                raise CatalogEnrichmentOutputLimitError()
            parsed = ParsedCatalogEnrichment(
                title=title,
                description=description,
                feature_bullets=self._deduplicate(bullets),
                search_keywords=self._deduplicate(keywords),
                technical_summary=summary,
            )
            if (
                len(parsed.feature_bullets) < 3
                or sum(len(item.fact_ids) for item in parsed.all_items()) > self._max_total_refs
            ):
                raise CatalogEnrichmentOutputLimitError()
            return parsed
        except (CatalogEnrichmentResponseInvalidError, CatalogEnrichmentOutputLimitError):
            raise
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise CatalogEnrichmentResponseInvalidError() from exc

    def _item(self, value: Any, max_characters: int) -> GroundedGeneratedText:
        if not isinstance(value, dict) or set(value) != _ITEM_KEYS:
            raise CatalogEnrichmentResponseInvalidError()
        text = value["text"]
        refs = value["factIds"]
        if (
            not isinstance(text, str)
            or not isinstance(refs, list)
            or not all(isinstance(item, str) for item in refs)
        ):
            raise CatalogEnrichmentResponseInvalidError()
        if len(text) > max_characters or len(refs) > self._max_refs:
            raise CatalogEnrichmentOutputLimitError()
        return GroundedGeneratedText(text=text, fact_ids=tuple(dict.fromkeys(refs)))

    def _items(self, value: Any, max_characters: int) -> tuple[GroundedGeneratedText, ...]:
        if not isinstance(value, list):
            raise CatalogEnrichmentResponseInvalidError()
        return tuple(self._item(item, max_characters) for item in value)

    @staticmethod
    def _deduplicate(
        items: tuple[GroundedGeneratedText, ...],
    ) -> tuple[GroundedGeneratedText, ...]:
        retained: list[GroundedGeneratedText] = []
        seen: set[str] = set()
        for item in items:
            key = " ".join(item.text.split()).casefold()
            if key not in seen:
                retained.append(item)
                seen.add(key)
        return tuple(retained)
