"""Central DynamoDB type and product item serialization."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, cast
from uuid import UUID

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from pydantic import BaseModel

from app.core.exceptions import ProductSerializationError
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
