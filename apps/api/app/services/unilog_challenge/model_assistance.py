"""Optional bounded model signal proposal; never receives or returns delivery answers."""

import json
from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.unilog_challenge import ObservedVocabulary, UnilogChallengeInputRow

MAX_MODEL_ATTEMPTS = 2


class UnilogSignalModelProvider(Protocol):
    def complete_json(self, payload: dict[str, object]) -> str: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidatedModelSignals:
    product_type: str | None
    attributes: tuple[tuple[str, str], ...]
    attempt_count: int


class UnilogModelSignalAssistant:
    def __init__(self, provider: UnilogSignalModelProvider) -> None:
        self._provider = provider

    def propose(
        self,
        row: UnilogChallengeInputRow,
        vocabulary: ObservedVocabulary | None = None,
    ) -> ValidatedModelSignals | None:
        payload = self._payload(row, vocabulary)
        for attempt in range(1, MAX_MODEL_ATTEMPTS + 1):
            try:
                parsed = json.loads(self._provider.complete_json(payload))
                product_type, attributes = self._validate(parsed, row.part_desc)
                return ValidatedModelSignals(
                    product_type=product_type,
                    attributes=attributes,
                    attempt_count=attempt,
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {**payload, "repair": "Return valid JSON using only exact source spans."}
        return None

    @staticmethod
    def _payload(
        row: UnilogChallengeInputRow, vocabulary: ObservedVocabulary | None
    ) -> dict[str, object]:
        return {
            "task": (
                "Extract productType and attribute name/value source spans; do not enrich facts."
            ),
            "rawInput": {
                "Mfg_Part_Num": row.mfg_part_num,
                "Part_Desc": row.part_desc,
                "brandCandidates": tuple(
                    value
                    for value in (
                        row.e1_brand_clean,
                        row.unilog_brand_clean,
                        row.dib_brand_clean,
                    )
                    if value is not None
                ),
            },
            "observedVocabulary": {
                "attributeLabels": ()
                if vocabulary is None
                else tuple(sorted(vocabulary.attribute_labels)),
                "uoms": () if vocabulary is None else tuple(sorted(vocabulary.uoms)),
            },
            "schema": {"productType": "string|null", "attributes": "[{name,value}]"},
        }

    @staticmethod
    def _validate(value: Any, source: str) -> tuple[str | None, tuple[tuple[str, str], ...]]:
        if not isinstance(value, dict) or set(value) != {"productType", "attributes"}:
            raise ValueError("model response schema is invalid")
        product_type = value["productType"]
        if product_type is not None and (
            not isinstance(product_type, str) or product_type.casefold() not in source.casefold()
        ):
            raise ValueError("model product type is not grounded")
        raw_attributes = value["attributes"]
        if not isinstance(raw_attributes, list) or len(raw_attributes) > 50:
            raise ValueError("model attributes are unbounded")
        attributes: list[tuple[str, str]] = []
        for item in raw_attributes:
            if (
                not isinstance(item, dict)
                or set(item) != {"name", "value"}
                or not isinstance(item["name"], str)
                or not isinstance(item["value"], str)
                or item["value"].casefold() not in source.casefold()
            ):
                raise ValueError("model attribute is not grounded")
            attributes.append((item["name"], item["value"]))
        return product_type, tuple(attributes)
