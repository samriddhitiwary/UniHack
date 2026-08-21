"""Deterministic, bounded vocabulary construction from the official dataset."""

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from enum import Enum
from typing import cast

from app.domain.unilog_challenge import UnilogChallengeInputRow, UnilogGroundTruthRecord
from app.domain.unilog_classification import (
    MAX_VOCABULARY_EXAMPLES,
    UNILOG_CLASSIFICATION_POLICY_VERSION,
    AbbreviationStatus,
    ClasspathMappingSource,
    UnilogClassificationVocabulary,
    UnilogObservedAbbreviation,
    UnilogProductTypeVocabularyEntry,
    UnilogVocabularyStatistics,
    VerifiedUnilogClasspathMapping,
    VocabularySource,
)
from app.services.unilog_classification.observed_rules import (
    GENERIC_PRODUCT_TERMS,
    OBSERVED_ABBREVIATION_RULES,
    OBSERVED_PHRASE_RULES,
    ObservedPhraseRule,
)


def normalize_product_phrase(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _span(text: str, variant: str) -> tuple[int, int] | None:
    tokens = re.findall(r"[a-z0-9]+", variant.casefold())
    if not tokens:
        return None
    pattern = r"(?<![a-z0-9])" + r"[\s\-_/]*".join(map(re.escape, tokens)) + r"(?![a-z0-9])"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.span() if match else None


def matched_rule(description: str) -> tuple[ObservedPhraseRule, str, tuple[int, int]] | None:
    matches: list[tuple[int, int, str, ObservedPhraseRule, tuple[int, int]]] = []
    for rule in OBSERVED_PHRASE_RULES:
        for variant in rule.variants:
            span = _span(description, variant)
            if span:
                matches.append((span[1] - span[0], len(variant), variant, rule, span))
    if not matches:
        return None
    _, _, variant, rule, span = max(matches, key=lambda item: (item[0], item[1], item[3].canonical))
    return rule, variant, span


def build_classification_vocabulary(
    rows: Iterable[UnilogChallengeInputRow],
    *,
    input_sha256: str,
    ground_truth_rows: Iterable[UnilogGroundTruthRecord] = (),
) -> UnilogClassificationVocabulary:
    ordered_rows = tuple(rows)
    by_key: dict[str, list[tuple[UnilogChallengeInputRow, str, ObservedPhraseRule]]] = defaultdict(
        list
    )
    unresolved: Counter[str] = Counter()
    generic_only = 0
    for row in ordered_rows:
        row_matches = []
        for rule in OBSERVED_PHRASE_RULES:
            observed = next(
                (
                    (variant, _span(row.part_desc, variant))
                    for variant in rule.variants
                    if _span(row.part_desc, variant)
                ),
                None,
            )
            if observed and observed[1] is not None:
                row_matches.append((rule, observed[0]))
        if row_matches:
            for rule, variant in row_matches:
                by_key[normalize_product_phrase(rule.canonical)].append((row, variant, rule))
        else:
            tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]*", row.part_desc)
            candidate = normalize_product_phrase(" ".join(tokens[-3:]))
            if candidate:
                unresolved[candidate] += 1
                if set(candidate.split()) <= GENERIC_PRODUCT_TERMS:
                    generic_only += 1

    entries: list[UnilogProductTypeVocabularyEntry] = []
    for key in sorted(by_key):
        observations = by_key[key]
        rule = observations[0][2]
        variants = tuple(
            sorted({item[1] for item in observations}, key=lambda value: value.casefold())
        )
        examples = tuple(dict.fromkeys(item[0].part_desc for item in observations))[
            :MAX_VOCABULARY_EXAMPLES
        ]
        entries.append(
            UnilogProductTypeVocabularyEntry(
                canonical_product_type=rule.canonical,
                normalized_key=key,
                product_family=rule.family,
                variants=variants,
                occurrence_count=len(observations),
                source=VocabularySource.OBSERVED_DATASET,
                support_count=len(observations),
                example_evidence=examples,
                manufacturer_evidence_count=sum(
                    bool(item[0].parsed_manufacturer) for item in observations
                ),
                brand_evidence_count=sum(
                    bool(
                        item[0].e1_brand_clean
                        or item[0].unilog_brand_clean
                        or item[0].dib_brand_clean
                    )
                    for item in observations
                ),
                confidence_bp=9_500 if len(observations) > 1 else 9_000,
            )
        )

    abbreviations = _build_abbreviations(ordered_rows)
    mappings = _build_verified_mappings(ordered_rows, tuple(ground_truth_rows))
    unresolved_candidates = tuple(
        value for value, _ in sorted(unresolved.items(), key=lambda item: (-item[1], item[0]))[:100]
    )
    statistics = UnilogVocabularyStatistics(
        input_rows=len(ordered_rows),
        unique_descriptions=len({row.part_desc for row in ordered_rows}),
        candidate_product_phrases=len(entries) + len(unresolved_candidates),
        canonical_product_types=len(entries),
        variants=sum(len(entry.variants) for entry in entries),
        verified_abbreviations=sum(
            item.status is AbbreviationStatus.VERIFIED_OBSERVED for item in abbreviations
        ),
        ambiguous_phrases=sum(
            item.status is AbbreviationStatus.AMBIGUOUS for item in abbreviations
        ),
        generic_only_phrases=generic_only,
        verified_classpath_mappings=len(mappings),
    )
    payload = _payload(entries, abbreviations, mappings, unresolved_candidates, statistics)
    vocabulary_hash = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return UnilogClassificationVocabulary(
        policy_version=UNILOG_CLASSIFICATION_POLICY_VERSION,
        input_sha256=input_sha256,
        vocabulary_hash=vocabulary_hash,
        entries=tuple(entries),
        abbreviations=abbreviations,
        verified_classpath_mappings=mappings,
        unresolved_candidates=unresolved_candidates,
        statistics=statistics,
    )


def _build_abbreviations(
    rows: tuple[UnilogChallengeInputRow, ...],
) -> tuple[UnilogObservedAbbreviation, ...]:
    result = []
    for rule in OBSERVED_ABBREVIATION_RULES:
        examples = [
            row.part_desc
            for row in rows
            if any(_span(row.part_desc, context) for context in rule.context_variants)
        ]
        if not examples:
            continue
        result.append(
            UnilogObservedAbbreviation(
                raw_token=rule.raw_token,
                expanded_phrase=rule.expanded_phrase,
                support_count=len(examples),
                evidence_examples=tuple(dict.fromkeys(examples))[:MAX_VOCABULARY_EXAMPLES],
                confidence_bp=5_000 if rule.ambiguous else 8_500,
                status=AbbreviationStatus.AMBIGUOUS
                if rule.ambiguous
                else AbbreviationStatus.VERIFIED_OBSERVED,
            )
        )
    return tuple(sorted(result, key=lambda item: item.raw_token.casefold()))


def _build_verified_mappings(
    rows: tuple[UnilogChallengeInputRow, ...], truths: tuple[UnilogGroundTruthRecord, ...]
) -> tuple[VerifiedUnilogClasspathMapping, ...]:
    by_id = {row.row_id: row for row in rows}
    candidates: dict[str, list[tuple[str, str | None, str | None, str | None]]] = defaultdict(list)
    for truth in truths:
        row = by_id.get(truth.input_row_id or "")
        if row is None:
            continue
        match = matched_rule(row.part_desc)
        classpath = truth.expected.value("Classpath")
        expected_type = truth.expected.value("Product Name")
        if not match or not isinstance(classpath, str) or not classpath.strip():
            continue
        canonical = match[0].canonical
        if isinstance(expected_type, str) and normalize_product_phrase(
            expected_type
        ) != normalize_product_phrase(canonical):
            continue
        candidates[canonical].append(
            (
                classpath.strip(),
                _text_or_none(truth.expected.value("Dept")),
                _text_or_none(truth.expected.value("Class")),
                _text_or_none(truth.expected.value("Fine")),
            )
        )
    result = []
    for product_type in sorted(candidates):
        values = candidates[product_type]
        if len(set(values)) != 1:
            continue
        classpath, department, class_name, fine = values[0]
        result.append(
            VerifiedUnilogClasspathMapping(
                product_type=product_type,
                classpath=classpath,
                department=department,
                class_name=class_name,
                fine=fine,
                mapping_source=ClasspathMappingSource.OFFICIAL_LABELLED_OUTPUT,
                support_count=len(values),
                verified=True,
                confidence_bp=9_500,
            )
        )
    return tuple(result)


def _text_or_none(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _payload(
    entries: Iterable[UnilogProductTypeVocabularyEntry],
    abbreviations: Iterable[UnilogObservedAbbreviation],
    mappings: Iterable[VerifiedUnilogClasspathMapping],
    unresolved: tuple[str, ...],
    statistics: UnilogVocabularyStatistics,
) -> dict[str, object]:
    from dataclasses import asdict

    def jsonable(value: object) -> object:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {str(key): jsonable(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [jsonable(item) for item in value]
        return value

    payload = jsonable(
        {
            "entries": [asdict(item) for item in entries],
            "abbreviations": [asdict(item) for item in abbreviations],
            "verifiedClasspathMappings": [asdict(item) for item in mappings],
            "unresolvedCandidates": unresolved,
            "statistics": asdict(statistics),
        }
    )
    return cast(dict[str, object], payload)
