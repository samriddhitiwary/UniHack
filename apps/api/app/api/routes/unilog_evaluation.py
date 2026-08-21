"""Explicit bounded APIs for challenge evaluation and dashboard reads."""

import base64
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status

from app.api.dependencies.unilog_evaluation import get_unilog_evaluation_service
from app.core.config import Settings, get_settings
from app.domain.unilog_evaluation import (
    FieldIssueType,
    UnilogEvaluationResult,
    UnilogFieldGroup,
    UnilogFieldMetric,
)
from app.services.unilog_evaluation.evaluation_service import UnilogEvaluationService
from app.services.unilog_evaluation.serialization import (
    serialize_evaluation_summary,
    serialize_labelled_row,
    serialize_value,
)

router = APIRouter(prefix="/unilog/evaluations", tags=["Unilog Evaluation"])


@router.post("", status_code=http_status.HTTP_201_CREATED)
def create_evaluation(
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    if (
        settings.unilog_challenge_input_path is None
        or settings.unilog_challenge_expected_output_path is None
    ):
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="Official Unilog challenge paths are not configured.",
        )
    result = service.create_from_paths(
        settings.unilog_challenge_input_path,
        settings.unilog_challenge_expected_output_path,
    )
    return serialize_evaluation_summary(result)


@router.get("/latest")
def get_latest_evaluation(
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
) -> dict[str, object]:
    result = service.latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No challenge evaluation exists.")
    return serialize_evaluation_summary(result)


@router.get("/{evaluation_id}")
def get_evaluation(
    evaluation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
) -> dict[str, object]:
    return serialize_evaluation_summary(_required(service, evaluation_id))


@router.get("/{evaluation_id}/summary")
def get_evaluation_summary(
    evaluation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
) -> dict[str, object]:
    return serialize_evaluation_summary(_required(service, evaluation_id))


@router.get("/{evaluation_id}/fields")
def get_evaluation_fields(
    evaluation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
    group: UnilogFieldGroup | None = None,
    issue_type: Annotated[FieldIssueType | None, Query(alias="issueType")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(min_length=1, max_length=512)] = None,
) -> dict[str, object]:
    result = _required(service, evaluation_id)
    items = tuple(
        item
        for item in result.field_metrics
        if (group is None or item.group is group) and _has_issue(item, issue_type)
    )
    offset = _decode_cursor(cursor, evaluation_id, group, issue_type)
    page = items[offset : offset + limit]
    next_offset = offset + len(page)
    return {
        "items": serialize_value(page),
        "nextCursor": (
            _encode_cursor(evaluation_id, next_offset, group, issue_type)
            if next_offset < len(items)
            else None
        ),
    }


@router.get("/{evaluation_id}/rows/{input_row_id}")
def get_labelled_row_comparison(
    evaluation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    input_row_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
) -> dict[str, object]:
    result = _required(service, evaluation_id)
    row = next((item for item in result.labelled_rows if item.input_row_id == input_row_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Labelled comparison not found.")
    return serialize_labelled_row(row)


@router.get("/{evaluation_id}/batch")
def get_batch_quality(
    evaluation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
) -> dict[str, object]:
    result = _required(service, evaluation_id)
    return {
        "batchMetrics": serialize_value(result.batch_metrics),
        "coverageMetrics": serialize_value(result.coverage_metrics),
        "descriptionMetrics": serialize_value(result.description_metrics),
        "reviewMetrics": serialize_value(result.review_metrics),
    }


@router.get("/{evaluation_id}/errors")
def get_error_analysis(
    evaluation_id: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    service: Annotated[UnilogEvaluationService, Depends(get_unilog_evaluation_service)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, object]:
    result = _required(service, evaluation_id)
    return {
        "problems": serialize_value(result.problems[:limit]),
        "recommendations": serialize_value(result.recommendations),
    }


def _required(service: UnilogEvaluationService, evaluation_id: str) -> UnilogEvaluationResult:
    result = service.get(evaluation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Challenge evaluation not found.")
    return result


def _has_issue(item: UnilogFieldMetric, issue: FieldIssueType | None) -> bool:
    if issue is None:
        return True
    return {
        FieldIssueType.MISMATCH: item.mismatch_count,
        FieldIssueType.MISSING_EXPECTED: item.missing_expected_count,
        FieldIssueType.UNEXPECTED_POPULATED: item.unexpected_populated_count,
        FieldIssueType.NORMALIZED_ONLY: item.normalized_count,
    }[issue] > 0


def _encode_cursor(
    evaluation_id: str,
    offset: int,
    group: UnilogFieldGroup | None,
    issue: FieldIssueType | None,
) -> str:
    payload = json.dumps(
        [evaluation_id, offset, group.value if group else None, issue.value if issue else None],
        separators=(",", ":"),
    ).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def _decode_cursor(
    cursor: str | None,
    evaluation_id: str,
    group: UnilogFieldGroup | None,
    issue: FieldIssueType | None,
) -> int:
    if cursor is None:
        return 0
    try:
        decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        scope_id, offset, scope_group, scope_issue = json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid evaluation cursor.") from exc
    expected = (group.value if group else None, issue.value if issue else None)
    if (
        scope_id != evaluation_id
        or (scope_group, scope_issue) != expected
        or isinstance(offset, bool)
        or not isinstance(offset, int)
        or not 0 <= offset <= 252
    ):
        raise HTTPException(status_code=400, detail="Evaluation cursor scope is invalid.")
    return int(offset)
