"""Raw, supported, strategy, and blank-field coverage over generated rows."""

from collections import Counter
from statistics import median_low

from app.domain.unilog_challenge import (
    FieldPopulationStrategy,
    UnilogBatchEnrichmentResult,
)
from app.domain.unilog_evaluation import (
    UnilogBlankFieldMetric,
    UnilogCoverageMetrics,
    UnilogFieldGroup,
    UnilogStrategyCoverage,
)
from app.services.unilog_challenge.field_strategy import UnilogFieldPopulationStrategy
from app.services.unilog_evaluation.field_comparator import field_group

_UNSUPPORTED_STRATEGIES = frozenset(
    {FieldPopulationStrategy.EXTERNAL_ONLY, FieldPopulationStrategy.UNSUPPORTED}
)


def evaluate_coverage(batch: UnilogBatchEnrichmentResult) -> UnilogCoverageMetrics:
    entries = UnilogFieldPopulationStrategy().entries()
    completed = tuple(item.enrichment for item in batch.rows if item.enrichment is not None)
    row_count = len(batch.rows)
    populated_per_row = [item.populated_field_count for item in completed]
    if len(completed) < row_count:
        populated_per_row.extend(0 for _ in range(row_count - len(completed)))
    supported_fields = tuple(
        entry.field for entry in entries if entry.strategy not in _UNSUPPORTED_STRATEGIES
    )
    by_strategy: dict[FieldPopulationStrategy, tuple[str, ...]] = {}
    for strategy in FieldPopulationStrategy:
        fields = tuple(entry.field for entry in entries if entry.strategy is strategy)
        if fields:
            by_strategy[strategy] = fields
    strategy_populated: Counter[FieldPopulationStrategy] = Counter()
    field_blank: Counter[str] = Counter()
    external_blank = external_possible = 0
    supported_populated = 0
    for enrichment in completed:
        values = enrichment.delivery_record.as_dict()
        for entry in entries:
            populated = values[entry.field] not in (None, "")
            if populated:
                strategy_populated[entry.strategy] += 1
                if entry.strategy not in _UNSUPPORTED_STRATEGIES:
                    supported_populated += 1
            elif entry.field in supported_fields:
                field_blank[entry.field] += 1
            if entry.strategy in _UNSUPPORTED_STRATEGIES:
                external_possible += 1
                if not populated:
                    external_blank += 1
    failed_count = row_count - len(completed)
    for field in supported_fields:
        field_blank[field] += failed_count
    for strategy, fields in by_strategy.items():
        if strategy in _UNSUPPORTED_STRATEGIES:
            external_possible += failed_count * len(fields)
            external_blank += failed_count * len(fields)
    possible_supported = row_count * len(supported_fields)
    strategy_metrics = tuple(
        UnilogStrategyCoverage(
            strategy=strategy,
            populated_count=strategy_populated[strategy],
            possible_count=row_count * len(fields),
            coverage_rate_bp=(
                strategy_populated[strategy] * 10_000 // (row_count * len(fields))
                if row_count
                else 0
            ),
        )
        for strategy, fields in by_strategy.items()
    )
    most_blank = tuple(
        UnilogBlankFieldMetric(
            field_name=field,
            group=field_group(field),
            blank_count=count,
            total_rows=row_count,
            blank_rate_bp=count * 10_000 // row_count if row_count else 0,
        )
        for field, count in sorted(
            field_blank.items(), key=lambda item: (-item[1], _blank_priority(item[0]), item[0])
        )[:20]
    )
    total_populated = sum(populated_per_row)
    return UnilogCoverageMetrics(
        row_count=row_count,
        average_populated_fields_bp=(total_populated * 100 // row_count if row_count else 0),
        median_populated_fields=median_low(populated_per_row) if populated_per_row else 0,
        minimum_populated_fields=min(populated_per_row, default=0),
        maximum_populated_fields=max(populated_per_row, default=0),
        raw_coverage_rate_bp=(total_populated * 10_000 // (row_count * 252) if row_count else 0),
        supported_field_count=len(supported_fields),
        supported_coverage_rate_bp=(
            supported_populated * 10_000 // possible_supported if possible_supported else 0
        ),
        strategy_coverage=strategy_metrics,
        most_blank_supported_fields=most_blank,
        external_or_unsupported_blank_rate_bp=(
            external_blank * 10_000 // external_possible if external_possible else 0
        ),
    )


def _blank_priority(field: str) -> int:
    group = field_group(field)
    if group in (
        UnilogFieldGroup.IDENTITY,
        UnilogFieldGroup.CLASSIFICATION,
        UnilogFieldGroup.DESCRIPTION,
    ):
        return 0
    if group is UnilogFieldGroup.FEATURE:
        return 1
    if group is UnilogFieldGroup.ATTRIBUTE:
        return 2
    return 3
