"""JSON persistence and cached loading for the reviewed classification artifact."""

import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.unilog_classification import (
    AbbreviationStatus,
    ClasspathMappingSource,
    UnilogClassificationVocabulary,
    UnilogObservedAbbreviation,
    UnilogProductTypeVocabularyEntry,
    UnilogVocabularyStatistics,
    VerifiedUnilogClasspathMapping,
    VocabularySource,
)

DEFAULT_VOCABULARY_PATH = (
    Path(__file__).parents[2] / "reference_data" / "unilog_classification_v1.json"
)


def write_classification_vocabulary(value: UnilogClassificationVocabulary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(asdict(value)), indent=2, sort_keys=True), encoding="utf-8"
    )
    temporary.replace(path)


def load_classification_vocabulary(path: Path) -> UnilogClassificationVocabulary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return UnilogClassificationVocabulary(
        policy_version=payload["policy_version"],
        input_sha256=payload["input_sha256"],
        vocabulary_hash=payload["vocabulary_hash"],
        entries=tuple(
            UnilogProductTypeVocabularyEntry(
                **{
                    key: value
                    for key, value in item.items()
                    if key not in {"source", "variants", "example_evidence"}
                },
                source=VocabularySource(item["source"]),
                variants=tuple(item["variants"]),
                example_evidence=tuple(item["example_evidence"]),
            )
            for item in payload["entries"]
        ),
        abbreviations=tuple(
            UnilogObservedAbbreviation(
                **{
                    key: value
                    for key, value in item.items()
                    if key not in {"status", "evidence_examples"}
                },
                status=AbbreviationStatus(item["status"]),
                evidence_examples=tuple(item["evidence_examples"]),
            )
            for item in payload["abbreviations"]
        ),
        verified_classpath_mappings=tuple(
            VerifiedUnilogClasspathMapping(
                **{key: value for key, value in item.items() if key != "mapping_source"},
                mapping_source=ClasspathMappingSource(item["mapping_source"]),
            )
            for item in payload["verified_classpath_mappings"]
        ),
        unresolved_candidates=tuple(payload["unresolved_candidates"]),
        statistics=UnilogVocabularyStatistics(**payload["statistics"]),
    )


@lru_cache(maxsize=1)
def load_default_classification_vocabulary() -> UnilogClassificationVocabulary:
    return load_classification_vocabulary(DEFAULT_VOCABULARY_PATH)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value
