"""Create SPEC-002 DynamoDB Local tables without deleting existing data."""

import logging
import time

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

CREATED_AT_INDEX = "CreatedAtIndex"
STATUS_CREATED_AT_INDEX = "StatusCreatedAtIndex"
logger = logging.getLogger(__name__)


def create_products_table() -> bool:
    """Create the configured products table; return True only when newly created."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("products")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "productId", "AttributeType": "S"},
                {"AttributeName": "entityType", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
                {"AttributeName": "status", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "productId", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": CREATED_AT_INDEX,
                    "KeySchema": [
                        {"AttributeName": "entityType", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": STATUS_CREATED_AT_INDEX,
                    "KeySchema": [
                        {"AttributeName": "status", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Products table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def wait_for_dynamodb(
    client: BaseClient, *, attempts: int = 20, delay: float = 0.25
) -> None:
    """Allow a newly started local container a short bounded startup window."""
    for attempt in range(1, attempts + 1):
        try:
            client.list_tables(Limit=1)
            return
        except (BotoCoreError, ClientError):
            if attempt == attempts:
                raise
            time.sleep(delay)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    create_products_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
