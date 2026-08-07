"""Central DynamoDB primitive and domain-item serialization."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import BaseModel

from app.core.exceptions import (
    ProcessingJobSerializationError,
    ProductSerializationError,
    ProductSourceSerializationError,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from app.domain.products.entities import Product
from app.domain.products.enums import ProductCategory, ProductStatus

AttributeValue = dict[str, Any]
WireItem = dict[str, AttributeValue]


def format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProductSerializationError("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def parse_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ProductSerializationError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProductSerializationError("timestamp is not valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProductSerializationError("timestamp must include a timezone")
    return parsed.astimezone(UTC)


def to_dynamodb_compatible(value: object) -> Any:
    """Recursively normalize supported values and reject Python floats."""
    if isinstance(value, float):
        raise ProductSerializationError("Python floats are not safe DynamoDB values")
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return format_utc(value)
    if isinstance(value, Enum):
        return to_dynamodb_compatible(value.value)
    if value is None or isinstance(value, (str, int, bool, Decimal)):
        return value
    if isinstance(value, BaseModel):
        return to_dynamodb_compatible(value.model_dump())
    if is_dataclass(value) and not isinstance(value, type):
        return to_dynamodb_compatible(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): to_dynamodb_compatible(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [to_dynamodb_compatible(item) for item in value]
    raise ProductSerializationError(f"unsupported DynamoDB value type: {type(value).__name__}")


def serialize_item(item: Mapping[str, object]) -> WireItem:
    serializer = TypeSerializer()
    try:
        return {
            key: cast(AttributeValue, serializer.serialize(to_dynamodb_compatible(value)))
            for key, value in item.items()
        }
    except ProductSerializationError:
        raise
    except (TypeError, ValueError) as exc:
        raise ProductSerializationError("item could not be serialized for DynamoDB") from exc


def deserialize_item(item: Mapping[str, AttributeValue]) -> dict[str, Any]:
    deserializer = TypeDeserializer()
    try:
        return {key: deserializer.deserialize(value) for key, value in item.items()}
    except (TypeError, ValueError) as exc:
        raise ProductSerializationError("DynamoDB item has invalid attribute values") from exc


def product_to_item(product: Product) -> dict[str, object]:
    return {
        "productId": product.product_id,
        "entityType": "PRODUCT",
        "name": product.name,
        "manufacturer": product.manufacturer,
        "modelNumber": product.model_number,
        "category": product.category,
        "status": product.status,
        "description": product.description,
        "sourceCount": product.source_count,
        "version": product.version,
        "createdAt": product.created_at,
        "updatedAt": product.updated_at,
    }


def product_from_item(item: Mapping[str, object]) -> Product:
    try:
        if item.get("entityType") != "PRODUCT":
            raise ValueError("unexpected entity type")
        return Product(
            product_id=UUID(str(item["productId"])),
            name=_required_string(item["name"], "name"),
            manufacturer=_optional_string(item.get("manufacturer")),
            model_number=_optional_string(item.get("modelNumber")),
            category=ProductCategory(str(item["category"])),
            status=ProductStatus(str(item["status"])),
            description=_optional_string(item.get("description")),
            source_count=_integer(item["sourceCount"], "sourceCount"),
            version=_integer(item["version"], "version"),
            created_at=parse_utc(item["createdAt"]),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except ProductSerializationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise ProductSerializationError("DynamoDB item is not a valid product") from exc


def product_source_to_item(source: ProductSource) -> dict[str, object]:
    return {
        "productId": source.product_id,
        "sourceId": source.source_id,
        "sourceType": source.source_type,
        "status": source.status,
        "originalFilename": source.original_filename,
        "storageKey": source.storage_key,
        "mimeType": source.mime_type,
        "fileSizeBytes": source.file_size_bytes,
        "checksumSha256": source.checksum_sha256,
        "displayName": source.display_name,
        "textContent": source.text_content,
        "errorMessage": source.error_message,
        "version": source.version,
        "createdAt": source.created_at,
        "updatedAt": source.updated_at,
    }


def product_source_from_item(item: Mapping[str, object]) -> ProductSource:
    try:
        return ProductSource(
            source_id=UUID(str(item["sourceId"])),
            product_id=UUID(str(item["productId"])),
            source_type=ProductSourceType(str(item["sourceType"])),
            status=ProductSourceStatus(str(item["status"])),
            original_filename=_optional_string(item.get("originalFilename")),
            storage_key=_optional_string(item.get("storageKey")),
            mime_type=_optional_string(item.get("mimeType")),
            file_size_bytes=_optional_integer(item.get("fileSizeBytes"), "fileSizeBytes"),
            checksum_sha256=_optional_string(item.get("checksumSha256")),
            display_name=_optional_string(item.get("displayName")),
            text_content=_optional_string(item.get("textContent")),
            error_message=_optional_string(item.get("errorMessage")),
            version=_integer(item["version"], "version"),
            created_at=parse_utc(item["createdAt"]),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except ProductSourceSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise ProductSourceSerializationError(
            "DynamoDB item is not a valid product source"
        ) from exc


def processing_job_source_scope(product_id: UUID, source_id: UUID) -> str:
    return f"{product_id}#{source_id}"


def processing_job_to_item(job: ProcessingJob) -> dict[str, object]:
    return {
        "jobId": job.job_id,
        "productId": job.product_id,
        "sourceId": job.source_id,
        "sourceScope": processing_job_source_scope(job.product_id, job.source_id),
        "jobType": job.job_type,
        "status": job.status,
        "attempt": job.attempt,
        "progressPercent": job.progress_percent,
        "errorCode": job.error_code,
        "errorMessage": job.error_message,
        "resultReference": job.result_reference,
        "version": job.version,
        "createdAt": job.created_at,
        "startedAt": job.started_at,
        "completedAt": job.completed_at,
        "updatedAt": job.updated_at,
    }


def processing_job_from_item(item: Mapping[str, object]) -> ProcessingJob:
    try:
        product_id = UUID(str(item["productId"]))
        source_id = UUID(str(item["sourceId"]))
        if item.get("sourceScope") != processing_job_source_scope(product_id, source_id):
            raise ValueError("sourceScope does not match job ownership")
        return ProcessingJob(
            job_id=UUID(str(item["jobId"])),
            product_id=product_id,
            source_id=source_id,
            job_type=ProcessingJobType(str(item["jobType"])),
            status=ProcessingJobStatus(str(item["status"])),
            attempt=_integer(item["attempt"], "attempt"),
            progress_percent=_integer(item["progressPercent"], "progressPercent"),
            error_code=_optional_string(item.get("errorCode")),
            error_message=_optional_string(item.get("errorMessage")),
            result_reference=_optional_string(item.get("resultReference")),
            version=_integer(item["version"], "version"),
            created_at=parse_utc(item["createdAt"]),
            started_at=_optional_datetime(item.get("startedAt")),
            completed_at=_optional_datetime(item.get("completedAt")),
            updated_at=parse_utc(item["updatedAt"]),
        )
    except ProcessingJobSerializationError:
        raise
    except (KeyError, TypeError, ValueError, ProductSerializationError) as exc:
        raise ProcessingJobSerializationError(
            "DynamoDB item is not a valid processing job"
        ) from exc


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional product text must be a string or null")
    return value


def _required_string(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise ValueError(f"{field} must be an integer")
    integer = int(value)
    if Decimal(integer) != value:
        raise ValueError(f"{field} must be an integer")
    return integer


def _optional_integer(value: object, field: str) -> int | None:
    if value is None:
        return None
    return _integer(value, field)


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    return parse_utc(value)
