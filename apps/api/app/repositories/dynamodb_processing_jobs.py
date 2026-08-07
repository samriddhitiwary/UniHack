"""DynamoDB processing-job repository."""

import logging
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.core.exceptions import (
    InvalidProcessingJobCursorError,
    ProcessingJobAlreadyExistsError,
    ProcessingJobNotFoundError,
    ProcessingJobRepositoryError,
    ProcessingJobSerializationError,
    ProcessingJobVersionConflictError,
    ProductSerializationError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobPage
from app.utils.cursors import (
    decode_processing_job_product_cursor,
    decode_processing_job_source_cursor,
    encode_processing_job_product_cursor,
    encode_processing_job_source_cursor,
)
from app.utils.dynamodb import (
    AttributeValue,
    WireItem,
    deserialize_item,
    processing_job_from_item,
    processing_job_source_scope,
    processing_job_to_item,
    serialize_item,
)

PRODUCT_CREATED_AT_INDEX = "ProductCreatedAtIndex"
SOURCE_CREATED_AT_INDEX = "SourceCreatedAtIndex"
MAX_JOB_PAGE_SIZE = 100
logger = logging.getLogger(__name__)


class DynamoDBProcessingJobRepository:
    def __init__(
        self,
        client: BaseClient,
        table_name: str,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._client = client
        self._table_name = table_name
        self._clock = clock or (lambda: datetime.now(UTC))

    def create(self, job: ProcessingJob) -> ProcessingJob:
        try:
            self._client.put_item(
                TableName=self._table_name,
                Item=serialize_item(processing_job_to_item(job)),
                ConditionExpression="attribute_not_exists(#jobId)",
                ExpressionAttributeNames={"#jobId": "jobId"},
            )
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                raise ProcessingJobAlreadyExistsError("processing job already exists") from exc
            raise ProcessingJobRepositoryError("processing job could not be created") from exc
        except BotoCoreError as exc:
            raise ProcessingJobRepositoryError("processing job could not be created") from exc
        logger.info(
            "event=processing_job.created job_id=%s product_id=%s source_id=%s "
            "job_type=%s attempt=%s",
            job.job_id,
            job.product_id,
            job.source_id,
            job.job_type.value,
            job.attempt,
        )
        return job

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None:
        try:
            response = self._client.get_item(
                TableName=self._table_name,
                Key=serialize_item({"jobId": job_id}),
                ConsistentRead=True,
            )
            raw = response.get("Item")
            if raw is None:
                return None
            job = _to_job(cast(Mapping[str, AttributeValue], raw))
        except ProcessingJobRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProcessingJobRepositoryError("processing job could not be retrieved") from exc
        logger.info("event=processing_job.retrieved job_id=%s", job_id)
        return job

    def list_by_product(
        self, product_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProcessingJobPage:
        _validate_limit(limit)
        start_key = decode_processing_job_product_cursor(cursor, product_id)
        expected_keys = {"jobId", "productId", "createdAt"}
        if start_key is not None and set(start_key) != expected_keys:
            raise InvalidProcessingJobCursorError("job cursor does not match product listing")
        return self._query_page(
            index_name=PRODUCT_CREATED_AT_INDEX,
            partition_name="productId",
            partition_value=product_id,
            limit=limit,
            start_key=start_key,
            cursor_encoder=lambda key: encode_processing_job_product_cursor(product_id, key),
            event_scope="product",
        )

    def list_by_source(
        self,
        product_id: UUID,
        source_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProcessingJobPage:
        _validate_limit(limit)
        start_key = decode_processing_job_source_cursor(cursor, product_id, source_id)
        expected_keys = {"jobId", "sourceScope", "createdAt"}
        if start_key is not None and set(start_key) != expected_keys:
            raise InvalidProcessingJobCursorError("job cursor does not match source listing")
        scope = processing_job_source_scope(product_id, source_id)
        return self._query_page(
            index_name=SOURCE_CREATED_AT_INDEX,
            partition_name="sourceScope",
            partition_value=scope,
            limit=limit,
            start_key=start_key,
            cursor_encoder=lambda key: encode_processing_job_source_cursor(
                product_id, source_id, key
            ),
            event_scope="source",
        )

    def _query_page(
        self,
        *,
        index_name: str,
        partition_name: str,
        partition_value: object,
        limit: int,
        start_key: dict[str, Any] | None,
        cursor_encoder: Callable[[WireItem | None], str | None],
        event_scope: str,
    ) -> ProcessingJobPage:
        request: dict[str, Any] = {
            "TableName": self._table_name,
            "IndexName": index_name,
            "KeyConditionExpression": "#scope = :scope",
            "ExpressionAttributeNames": {"#scope": partition_name},
            "ExpressionAttributeValues": serialize_item({":scope": partition_value}),
            "ScanIndexForward": False,
            "Limit": limit,
        }
        if start_key is not None:
            request["ExclusiveStartKey"] = start_key
        try:
            response = self._client.query(**request)
            raw_items = cast(list[Mapping[str, AttributeValue]], response.get("Items", []))
            items = tuple(_to_job(item) for item in raw_items)
            last_key = cast(WireItem | None, response.get("LastEvaluatedKey"))
            page = ProcessingJobPage(items=items, next_cursor=cursor_encoder(last_key))
        except ProcessingJobRepositoryError:
            raise
        except (BotoCoreError, ClientError) as exc:
            raise ProcessingJobRepositoryError("processing jobs could not be listed") from exc
        logger.info(
            "event=processing_job.listed scope=%s result_count=%s has_next_cursor=%s",
            event_scope,
            len(page.items),
            page.next_cursor is not None,
        )
        return page

    def update(self, job: ProcessingJob, expected_version: int) -> ProcessingJob:
        _validate_expected_version(expected_version)
        values = serialize_item(
            {
                ":status": job.status,
                ":progressPercent": job.progress_percent,
                ":errorCode": job.error_code,
                ":errorMessage": job.error_message,
                ":resultReference": job.result_reference,
                ":startedAt": job.started_at,
                ":completedAt": job.completed_at,
                ":updatedAt": self._clock().astimezone(UTC),
                ":newVersion": expected_version + 1,
                ":expectedVersion": expected_version,
            }
        )
        try:
            response = self._client.update_item(
                TableName=self._table_name,
                Key=serialize_item({"jobId": job.job_id}),
                UpdateExpression=(
                    "SET #status = :status, #progressPercent = :progressPercent, "
                    "#errorCode = :errorCode, #errorMessage = :errorMessage, "
                    "#resultReference = :resultReference, #startedAt = :startedAt, "
                    "#completedAt = :completedAt, #updatedAt = :updatedAt, "
                    "#version = :newVersion"
                ),
                ConditionExpression="attribute_exists(#jobId) AND #version = :expectedVersion",
                ExpressionAttributeNames={
                    "#jobId": "jobId",
                    "#status": "status",
                    "#progressPercent": "progressPercent",
                    "#errorCode": "errorCode",
                    "#errorMessage": "errorMessage",
                    "#resultReference": "resultReference",
                    "#startedAt": "startedAt",
                    "#completedAt": "completedAt",
                    "#updatedAt": "updatedAt",
                    "#version": "version",
                },
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
            raw = response.get("Attributes")
            if raw is None:
                raise ProcessingJobRepositoryError("updated processing job was not returned")
            stored = _to_job(cast(Mapping[str, AttributeValue], raw))
        except ClientError as exc:
            if _error_code(exc) == "ConditionalCheckFailedException":
                current = self.get_by_id(job.job_id)
                if current is None:
                    raise ProcessingJobNotFoundError("processing job does not exist") from exc
                raise ProcessingJobVersionConflictError("processing job version is stale") from exc
            raise ProcessingJobRepositoryError("processing job could not be updated") from exc
        except BotoCoreError as exc:
            raise ProcessingJobRepositoryError("processing job could not be updated") from exc
        logger.info(
            "event=processing_job.updated job_id=%s status=%s progress=%s version=%s",
            stored.job_id,
            stored.status.value,
            stored.progress_percent,
            stored.version,
        )
        return stored


def _to_job(item: Mapping[str, AttributeValue]) -> ProcessingJob:
    try:
        return processing_job_from_item(deserialize_item(item))
    except ProcessingJobSerializationError:
        raise
    except ProductSerializationError as exc:
        raise ProcessingJobSerializationError("DynamoDB item is not a valid job") from exc


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError(f"limit must be between 1 and {MAX_JOB_PAGE_SIZE}")


def _validate_expected_version(expected_version: int) -> None:
    if (
        isinstance(expected_version, bool)
        or not isinstance(expected_version, int)
        or expected_version < 1
    ):
        raise ValueError("expected_version must be a positive integer")


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))
