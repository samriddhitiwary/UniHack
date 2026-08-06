"""DynamoDB dependency construction."""

from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from app.core.config import Settings, get_settings


class DynamoDBHealth:
    """Small dependency used only to check DynamoDB availability."""

    def __init__(self, client: BaseClient) -> None:
        self._client = client

    def check(self) -> None:
        """Raise when DynamoDB cannot answer a minimal control-plane request."""
        self._client.list_tables(Limit=1)


def create_dynamodb_client(settings: Settings) -> BaseClient:
    """Create one client that works with DynamoDB Local and AWS DynamoDB."""
    options: dict[str, object] = {
        "region_name": settings.aws_region,
        "config": Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 1}),
    }
    if settings.dynamodb_endpoint_url:
        options.update(
            endpoint_url=settings.dynamodb_endpoint_url,
            aws_access_key_id="local",
            aws_secret_access_key="local",
        )
    return boto3.client("dynamodb", **options)


@lru_cache
def get_dynamodb_client() -> BaseClient:
    """Return the reusable deployment-aware DynamoDB client."""
    return create_dynamodb_client(get_settings())


@lru_cache
def get_dynamodb_health() -> DynamoDBHealth:
    """Return a process-wide reusable health dependency."""
    return DynamoDBHealth(get_dynamodb_client())
