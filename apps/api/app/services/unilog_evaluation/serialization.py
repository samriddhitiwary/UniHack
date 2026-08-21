"""Stable camel-case JSON views for evaluation APIs and report artifacts."""

from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, cast

from app.domain.unilog_evaluation import UnilogEvaluationResult, UnilogLabelledRowEvaluation
from app.schemas.products.models import to_camel


def serialize_evaluation_summary(result: UnilogEvaluationResult) -> dict[str, object]:
    return {
        "evaluationId": result.evaluation_id,
        "datasetFingerprint": result.dataset_fingerprint,
        "generatedBatchFingerprint": result.generated_batch_fingerprint,
        "policyVersion": result.policy_version,
        "labelledRowCount": result.labelled_row_count,
        "createdAt": result.created_at,
        "accuracy": _serialize(result.accuracy),
        "groupMetrics": _serialize(result.group_metrics),
        "attributeMetrics": _serialize(result.attribute_metrics),
        "coverageMetrics": _serialize(result.coverage_metrics),
        "descriptionMetrics": _serialize(result.description_metrics),
        "reviewMetrics": _serialize(result.review_metrics),
        "batchMetrics": _serialize(result.batch_metrics),
        "problems": _serialize(result.problems[:20]),
        "recommendations": _serialize(result.recommendations),
        "labelledRows": [
            {
                "inputRowId": row.input_row_id,
                "mfgPartNum": row.mfg_part_num,
                "accuracy": _serialize(row.accuracy),
            }
            for row in result.labelled_rows
        ],
    }


def serialize_labelled_row(row: UnilogLabelledRowEvaluation) -> dict[str, object]:
    return cast(dict[str, object], _serialize(row))


def serialize_value(value: object) -> Any:
    return _serialize(value)


def _serialize(value: object) -> Any:
    if value is None or isinstance(value, str | int | float | bool | datetime):
        return value
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            to_camel(field.name): _serialize(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_serialize(item) for item in value]
    raise TypeError(f"unsupported evaluation serialization type: {type(value).__name__}")
