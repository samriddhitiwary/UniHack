"""Composite DynamoDB persistence for attribute validation results."""

import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    AttributeValidationRepositoryError,
    AttributeValidationResultAlreadyExistsError,
    AttributeValidationResultItemTooLargeError,
    AttributeValidationSerializationError,
)
from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.attribute_validation import (
    AttributeValidationIssue,
    AttributeValidationResult,
    AttributeValidationResultStatus,
    AttributeValidationSummary,
    CandidateValidationAssessment,
    CandidateValidationStatus,
    ValidationIssueSeverity,
    ValidationIssueType,
)
from app.domain.category_schemas import AttributeDataType
from app.domain.products import ProductCategory
from app.utils.dynamodb import AttributeValue, WireItem, deserialize_item, parse_utc, serialize_item

JOB_ID_INDEX = "JobIdIndex"
MAX_SAFE_ITEM_BYTES = 390_000


class DynamoDBAttributeValidationResultRepository:
    def __init__(self, client: BaseClient, table_name: str) -> None:
        self._client, self._table_name = client, table_name

    def create(self, result: AttributeValidationResult) -> AttributeValidationResult:
        records = [self._meta(result)]
        records.extend(
            self._assessment(result.validation_id, i, value)
            for i, value in enumerate(result.assessments, 1)
        )
        records.extend(
            self._summary(result.validation_id, i, value)
            for i, value in enumerate(result.attribute_summaries, 1)
        )
        wire = [serialize_item(record) for record in records]
        if any(
            len(json.dumps(item, separators=(",", ":"), default=str).encode()) > MAX_SAFE_ITEM_BYTES
            for item in wire
        ):
            raise AttributeValidationResultItemTooLargeError()
        try:
            for item in wire:
                self._client.put_item(
                    TableName=self._table_name,
                    Item=item,
                    ConditionExpression="attribute_not_exists(#recordKey)",
                    ExpressionAttributeNames={"#recordKey": "recordKey"},
                )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise AttributeValidationResultAlreadyExistsError() from exc
            raise AttributeValidationRepositoryError() from exc
        except BotoCoreError as exc:
            raise AttributeValidationRepositoryError() from exc
        return result

    def get_by_id(self, validation_id: UUID) -> AttributeValidationResult | None:
        items: list[Mapping[str, AttributeValue]] = []
        start: WireItem | None = None
        try:
            while True:
                request: dict[str, Any] = {
                    "TableName": self._table_name,
                    "KeyConditionExpression": "#id = :id",
                    "ExpressionAttributeNames": {"#id": "validationId"},
                    "ExpressionAttributeValues": serialize_item({":id": validation_id}),
                    "ConsistentRead": True,
                }
                if start:
                    request["ExclusiveStartKey"] = start
                response = self._client.query(**request)
                items.extend(cast(list[Mapping[str, AttributeValue]], response.get("Items", [])))
                start = cast(WireItem | None, response.get("LastEvaluatedKey"))
                if not start:
                    break
            return self._from_items([deserialize_item(item) for item in items]) if items else None
        except AttributeValidationRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeValidationRepositoryError() from exc

    def get_by_job_id(self, job_id: UUID) -> AttributeValidationResult | None:
        try:
            response = self._client.query(
                TableName=self._table_name,
                IndexName=JOB_ID_INDEX,
                KeyConditionExpression="#jobId = :jobId",
                ExpressionAttributeNames={"#jobId": "jobId"},
                ExpressionAttributeValues=serialize_item({":jobId": job_id}),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            if not items:
                return None
            return self.get_by_id(UUID(str(deserialize_item(items[0])["validationId"])))
        except AttributeValidationRepositoryError:
            raise
        except (BotoCoreError, ClientError, KeyError, ValueError, TypeError) as exc:
            raise AttributeValidationRepositoryError() from exc

    @staticmethod
    def _meta(result: AttributeValidationResult) -> dict[str, Any]:
        return {
            "validationId": result.validation_id,
            "recordKey": "META",
            "jobId": result.job_id,
            "productId": result.product_id,
            "normalizationId": result.normalization_id,
            "extractionId": result.extraction_id,
            "classificationId": result.classification_id,
            "category": result.category,
            "schemaVersion": result.schema_version,
            "schemaFingerprint": result.schema_fingerprint,
            "status": result.status,
            "candidateCount": result.candidate_count,
            "validCount": result.valid_count,
            "validWithWarningsCount": result.valid_with_warnings_count,
            "invalidCount": result.invalid_count,
            "notValidatableCount": result.not_validatable_count,
            "issueCount": result.issue_count,
            "errorCount": result.error_count,
            "warningCount": result.warning_count,
            "attributeSummaryCount": result.attribute_summary_count,
            "warningCodes": list(result.warning_codes),
            "engine": result.engine,
            "engineVersion": result.engine_version,
            "createdAt": result.created_at,
        }

    @staticmethod
    def _assessment(
        validation_id: UUID, index: int, item: CandidateValidationAssessment
    ) -> dict[str, Any]:
        return {
            "validationId": validation_id,
            "recordKey": f"ASSESSMENT#{index:06d}",
            "assessmentId": item.assessment_id,
            "normalizedCandidateId": item.normalized_candidate_id,
            "sourceCandidateId": item.source_candidate_id,
            "attributeName": item.attribute_name,
            "attributeDisplayName": item.attribute_display_name,
            "dataType": item.data_type,
            "status": item.status,
            "normalizedValue": item.normalized_value,
            "normalizedUnit": item.normalized_unit,
            "issueCount": item.issue_count,
            "errorCount": item.error_count,
            "warningCount": item.warning_count,
            "issues": list(item.issues),
            "sourceId": item.source_id,
            "evidenceType": item.evidence_type,
            "evidenceLocation": item.evidence_location,
            "createdAt": item.created_at,
        }

    @staticmethod
    def _summary(
        validation_id: UUID, index: int, item: AttributeValidationSummary
    ) -> dict[str, Any]:
        return {
            "validationId": validation_id,
            "recordKey": f"SUMMARY#{index:06d}",
            "attributeName": item.attribute_name,
            "candidateCount": item.candidate_count,
            "validCandidateCount": item.valid_candidate_count,
            "validWithWarningsCandidateCount": item.valid_with_warnings_candidate_count,
            "invalidCandidateCount": item.invalid_candidate_count,
            "notValidatableCount": item.not_validatable_count,
            "issueCount": item.issue_count,
        }

    @staticmethod
    def _from_items(items: list[dict[str, Any]]) -> AttributeValidationResult:
        try:
            meta = next(item for item in items if item["recordKey"] == "META")
            raw_assessments = sorted(
                (i for i in items if str(i["recordKey"]).startswith("ASSESSMENT#")),
                key=lambda i: str(i["recordKey"]),
            )
            raw_summaries = sorted(
                (i for i in items if str(i["recordKey"]).startswith("SUMMARY#")),
                key=lambda i: str(i["recordKey"]),
            )
            assessments = tuple(
                CandidateValidationAssessment(
                    assessment_id=UUID(str(i["assessmentId"])),
                    normalized_candidate_id=str(i["normalizedCandidateId"]),
                    source_candidate_id=str(i["sourceCandidateId"]),
                    attribute_name=str(i["attributeName"]),
                    attribute_display_name=str(i["attributeDisplayName"]),
                    data_type=AttributeDataType(str(i["dataType"])),
                    status=CandidateValidationStatus(str(i["status"])),
                    normalized_value=None
                    if i.get("normalizedValue") is None
                    else str(i["normalizedValue"]),
                    normalized_unit=None
                    if i.get("normalizedUnit") is None
                    else str(i["normalizedUnit"]),
                    issue_count=int(i["issueCount"]),
                    error_count=int(i["errorCount"]),
                    warning_count=int(i["warningCount"]),
                    issues=tuple(_issue(v) for v in i["issues"]),
                    source_id=UUID(str(i["sourceId"])),
                    evidence_type=AttributeExtractionEvidenceType(str(i["evidenceType"])),
                    evidence_location=str(i["evidenceLocation"]),
                    created_at=parse_utc(i["createdAt"]),
                )
                for i in raw_assessments
            )
            summaries = tuple(
                AttributeValidationSummary(
                    attribute_name=str(i["attributeName"]),
                    candidate_count=int(i["candidateCount"]),
                    valid_candidate_count=int(i["validCandidateCount"]),
                    valid_with_warnings_candidate_count=int(i["validWithWarningsCandidateCount"]),
                    invalid_candidate_count=int(i["invalidCandidateCount"]),
                    not_validatable_count=int(i["notValidatableCount"]),
                    issue_count=int(i["issueCount"]),
                )
                for i in raw_summaries
            )
            return AttributeValidationResult(
                validation_id=UUID(str(meta["validationId"])),
                job_id=UUID(str(meta["jobId"])),
                product_id=UUID(str(meta["productId"])),
                normalization_id=UUID(str(meta["normalizationId"])),
                extraction_id=UUID(str(meta["extractionId"])),
                classification_id=UUID(str(meta["classificationId"])),
                category=ProductCategory(str(meta["category"])),
                schema_version=int(meta["schemaVersion"]),
                schema_fingerprint=str(meta["schemaFingerprint"]),
                status=AttributeValidationResultStatus(str(meta["status"])),
                candidate_count=int(meta["candidateCount"]),
                valid_count=int(meta["validCount"]),
                valid_with_warnings_count=int(meta["validWithWarningsCount"]),
                invalid_count=int(meta["invalidCount"]),
                not_validatable_count=int(meta["notValidatableCount"]),
                issue_count=int(meta["issueCount"]),
                error_count=int(meta["errorCount"]),
                warning_count=int(meta["warningCount"]),
                attribute_summary_count=int(meta["attributeSummaryCount"]),
                assessments=assessments,
                attribute_summaries=summaries,
                warning_codes=tuple(str(v) for v in meta.get("warningCodes", [])),
                engine=str(meta["engine"]),
                engine_version=str(meta["engineVersion"]),
                created_at=parse_utc(meta["createdAt"]),
            )
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise AttributeValidationSerializationError() from exc


def _issue(value: Mapping[str, Any]) -> AttributeValidationIssue:
    return AttributeValidationIssue(
        issue_id=str(value["issue_id"]),
        issue_type=ValidationIssueType(str(value["issue_type"])),
        severity=ValidationIssueSeverity(str(value["severity"])),
        message_code=str(value["message_code"]),
        expected=None if value.get("expected") is None else str(value["expected"]),
        actual=None if value.get("actual") is None else str(value["actual"]),
    )
