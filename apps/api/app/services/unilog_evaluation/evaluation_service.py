"""Reproducible evaluation orchestration with post-enrichment ground-truth access."""

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from app.domain.unilog_challenge import (
    UnilogBatchEnrichmentResult,
    UnilogGroundTruthRecord,
)
from app.domain.unilog_evaluation import (
    UNILOG_EVALUATION_POLICY_VERSION,
    EvaluationMatchStatus,
    UnilogEvaluationResult,
    UnilogFieldEvaluation,
    UnilogFieldGroup,
    UnilogFieldMetric,
    UnilogGroupMetrics,
    UnilogLabelledRowEvaluation,
)
from app.importers.unilog_challenge.parsers import parse_expected_output_csv, parse_input_csv
from app.repositories.unilog_evaluation import UnilogEvaluationRepository
from app.services.unilog_challenge.batch_enrichment import UnilogBatchEnrichmentService
from app.services.unilog_challenge.ground_truth import align_ground_truth, attach_alignments
from app.services.unilog_evaluation.attribute_comparator import evaluate_attributes
from app.services.unilog_evaluation.attribute_coverage_evaluator import evaluate_attribute_coverage
from app.services.unilog_evaluation.batch_evaluator import evaluate_batch_quality
from app.services.unilog_evaluation.classification_evaluator import evaluate_classification
from app.services.unilog_evaluation.coverage_evaluator import evaluate_coverage
from app.services.unilog_evaluation.description_compliance import (
    evaluate_description_compliance,
)
from app.services.unilog_evaluation.error_analysis import analyze_field_errors
from app.services.unilog_evaluation.field_comparator import (
    accuracy_metrics,
    compare_delivery_field,
)
from app.services.unilog_evaluation.identity_evaluator import evaluate_identity_resolution


class UnilogEvaluationService:
    def __init__(
        self,
        repository: UnilogEvaluationRepository,
        *,
        now: Callable[[], datetime] | None = None,
        batch_service: UnilogBatchEnrichmentService | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))
        self._batch = batch_service or UnilogBatchEnrichmentService()

    def create_from_paths(
        self, input_path: Path, expected_output_path: Path
    ) -> UnilogEvaluationResult:
        started_at = self._now()
        _, inputs = parse_input_csv(input_path, imported_at=started_at)
        generated = self._batch.enrich_batch(inputs)
        output_metadata, raw_truth = parse_expected_output_csv(
            expected_output_path, imported_at=started_at
        )
        aligned = attach_alignments(raw_truth, align_ground_truth(inputs, raw_truth))
        result = self.evaluate(
            generated,
            aligned,
            dataset_fingerprint=output_metadata.sha256,
            created_at=started_at,
        )
        self._repository.save(result)
        return result

    def evaluate(
        self,
        batch: UnilogBatchEnrichmentResult,
        truth_rows: tuple[UnilogGroundTruthRecord, ...],
        *,
        dataset_fingerprint: str,
        created_at: datetime | None = None,
    ) -> UnilogEvaluationResult:
        actual_by_id = {
            item.input_row_id: item.enrichment for item in batch.rows if item.enrichment is not None
        }
        labelled: list[UnilogLabelledRowEvaluation] = []
        pairs = []
        all_comparisons: list[UnilogFieldEvaluation] = []
        for truth in truth_rows:
            if truth.input_row_id is None or truth.input_row_id not in actual_by_id:
                raise ValueError("labelled row is not uniquely aligned to a generated result")
            actual_result = actual_by_id[truth.input_row_id]
            if actual_result is None:
                raise ValueError("labelled generated result is unavailable")
            comparisons = tuple(
                compare_delivery_field(
                    field,
                    None if expected is None else str(expected),
                    None
                    if actual_result.delivery_record.value(field) is None
                    else str(actual_result.delivery_record.value(field)),
                )
                for field, expected in truth.expected.as_dict().items()
            )
            all_comparisons.extend(comparisons)
            pairs.append((truth.expected, actual_result.delivery_record))
            labelled.append(
                UnilogLabelledRowEvaluation(
                    input_row_id=truth.input_row_id,
                    mfg_part_num=truth.mfg_part_num,
                    comparisons=comparisons,
                    accuracy=accuracy_metrics(comparisons),
                )
            )
        comparisons_tuple = tuple(all_comparisons)
        accuracy = accuracy_metrics(comparisons_tuple)
        groups = self._group_metrics(comparisons_tuple)
        attributes = evaluate_attributes(tuple(pairs))
        attribute_coverage = evaluate_attribute_coverage(batch)
        coverage = evaluate_coverage(batch)
        descriptions = evaluate_description_compliance(batch)
        review, batch_metrics = evaluate_batch_quality(batch)
        classification = evaluate_classification(batch)
        identity = evaluate_identity_resolution(batch, tuple(pairs))
        field_metrics = self._field_metrics(comparisons_tuple)
        problems, recommendations = analyze_field_errors(comparisons_tuple, attributes, review)
        generated_fingerprint = self._batch_fingerprint(batch)
        evaluation_id = hashlib.sha256(
            f"{dataset_fingerprint}:{generated_fingerprint}:{UNILOG_EVALUATION_POLICY_VERSION}".encode()
        ).hexdigest()
        return UnilogEvaluationResult(
            evaluation_id=evaluation_id,
            dataset_fingerprint=dataset_fingerprint,
            generated_batch_fingerprint=generated_fingerprint,
            policy_version=UNILOG_EVALUATION_POLICY_VERSION,
            labelled_row_count=len(labelled),
            accuracy=accuracy,
            group_metrics=groups,
            attribute_metrics=attributes,
            attribute_coverage_metrics=attribute_coverage,
            coverage_metrics=coverage,
            description_metrics=descriptions,
            review_metrics=review,
            batch_metrics=batch_metrics,
            classification_metrics=classification,
            identity_resolution_metrics=identity,
            field_metrics=field_metrics,
            problems=problems,
            recommendations=recommendations,
            labelled_rows=tuple(labelled),
            created_at=created_at or self._now(),
        )

    def get(self, evaluation_id: str) -> UnilogEvaluationResult | None:
        return self._repository.get(evaluation_id)

    def latest(self) -> UnilogEvaluationResult | None:
        return self._repository.latest()

    @staticmethod
    def _group_metrics(
        comparisons: tuple[UnilogFieldEvaluation, ...],
    ) -> tuple[UnilogGroupMetrics, ...]:
        results = []
        for group in UnilogFieldGroup:
            items = tuple(item for item in comparisons if item.group is group)
            expected_populated = sum(item.expected_value is not None for item in items)
            actual_populated = sum(item.actual_value is not None for item in items)
            expected_recovered = sum(
                item.expected_value is not None and item.actual_value is not None for item in items
            )
            results.append(
                UnilogGroupMetrics(
                    group=group,
                    accuracy=accuracy_metrics(items),
                    labelled_populated_count=expected_populated,
                    generated_populated_count=actual_populated,
                    coverage_rate_bp=(
                        expected_recovered * 10_000 // expected_populated
                        if expected_populated
                        else 0
                    ),
                )
            )
        return tuple(results)

    @staticmethod
    def _field_metrics(
        comparisons: tuple[UnilogFieldEvaluation, ...],
    ) -> tuple[UnilogFieldMetric, ...]:
        from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS

        by_field: dict[str, list[UnilogFieldEvaluation]] = {
            field: [] for field in UNILOG_DELIVERY_HEADERS
        }
        for item in comparisons:
            by_field[item.field_name].append(item)
        metrics = []
        for field, items in by_field.items():
            statuses = Counter(item.status for item in items)
            metrics.append(
                UnilogFieldMetric(
                    field_name=field,
                    group=items[0].group,
                    exact_count=statuses[EvaluationMatchStatus.EXACT_MATCH],
                    normalized_count=statuses[EvaluationMatchStatus.NORMALIZED_MATCH],
                    mismatch_count=statuses[EvaluationMatchStatus.MISMATCH],
                    missing_expected_count=statuses[
                        EvaluationMatchStatus.EXPECTED_POPULATED_ACTUAL_BLANK
                    ],
                    unexpected_populated_count=statuses[
                        EvaluationMatchStatus.EXPECTED_BLANK_ACTUAL_POPULATED
                    ],
                    both_blank_count=statuses[EvaluationMatchStatus.BOTH_BLANK],
                )
            )
        return tuple(metrics)

    @staticmethod
    def _batch_fingerprint(batch: UnilogBatchEnrichmentResult) -> str:
        payload = []
        for item in batch.rows:
            payload.append(
                {
                    "inputRowId": item.input_row_id,
                    "status": item.status.value,
                    "record": (
                        item.enrichment.delivery_record.as_dict()
                        if item.enrichment is not None
                        else None
                    ),
                    "warnings": item.enrichment.warnings if item.enrichment is not None else (),
                    "confidenceBp": (
                        item.enrichment.overall_confidence_bp
                        if item.enrichment is not None
                        else None
                    ),
                }
            )
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()
