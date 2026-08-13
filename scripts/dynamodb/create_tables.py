"""Create configured DynamoDB Local tables without deleting existing data."""

import logging
import time

from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings

CREATED_AT_INDEX = "CreatedAtIndex"
STATUS_CREATED_AT_INDEX = "StatusCreatedAtIndex"
PRODUCT_CREATED_AT_INDEX = "ProductCreatedAtIndex"
SOURCE_CREATED_AT_INDEX = "SourceCreatedAtIndex"
JOB_ID_INDEX = "JobIdIndex"
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


def create_sources_table() -> bool:
    """Create the configured product-sources table; return True only when new."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("sources")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "productId", "AttributeType": "S"},
                {"AttributeName": "sourceId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "productId", "KeyType": "HASH"},
                {"AttributeName": "sourceId", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": PRODUCT_CREATED_AT_INDEX,
                    "KeySchema": [
                        {"AttributeName": "productId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Sources table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def create_processing_jobs_table() -> bool:
    """Create the configured processing-jobs table; return True only when new."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("processing-jobs")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "productId", "AttributeType": "S"},
                {"AttributeName": "sourceScope", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[{"AttributeName": "jobId", "KeyType": "HASH"}],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": PRODUCT_CREATED_AT_INDEX,
                    "KeySchema": [
                        {"AttributeName": "productId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": SOURCE_CREATED_AT_INDEX,
                    "KeySchema": [
                        {"AttributeName": "sourceScope", "KeyType": "HASH"},
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
        "Processing-jobs table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def create_extraction_results_table() -> bool:
    """Create the configured extraction-results table; return True only when new."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("extraction-results")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "extractionId", "AttributeType": "S"},
                {"AttributeName": "recordKey", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "extractionId", "KeyType": "HASH"},
                {"AttributeName": "recordKey", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": JOB_ID_INDEX,
                    "KeySchema": [
                        {"AttributeName": "jobId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Extraction-results table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def create_table_extraction_results_table() -> bool:
    """Create the configured table-extraction-results table idempotently."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("table-extraction-results")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "extractionId", "AttributeType": "S"},
                {"AttributeName": "recordKey", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "extractionId", "KeyType": "HASH"},
                {"AttributeName": "recordKey", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": JOB_ID_INDEX,
                    "KeySchema": [
                        {"AttributeName": "jobId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Table-extraction-results table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def create_csv_processing_results_table() -> bool:
    """Create the configured CSV processing-results table idempotently."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("csv-processing-results")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "processingId", "AttributeType": "S"},
                {"AttributeName": "recordKey", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "processingId", "KeyType": "HASH"},
                {"AttributeName": "recordKey", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": JOB_ID_INDEX,
                    "KeySchema": [
                        {"AttributeName": "jobId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "CSV processing-results table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def create_image_analysis_results_table() -> bool:
    """Create the configured image-analysis-results table idempotently."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("image-analysis-results")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "analysisId", "AttributeType": "S"},
                {"AttributeName": "recordKey", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "analysisId", "KeyType": "HASH"},
                {"AttributeName": "recordKey", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": JOB_ID_INDEX,
                    "KeySchema": [
                        {"AttributeName": "jobId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Image-analysis-results table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def create_image_ocr_results_table() -> bool:
    """Create the configured image-ocr-results table idempotently."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("image-ocr-results")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "ocrId", "AttributeType": "S"},
                {"AttributeName": "recordKey", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "ocrId", "KeyType": "HASH"},
                {"AttributeName": "recordKey", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": JOB_ID_INDEX,
                    "KeySchema": [
                        {"AttributeName": "jobId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Image OCR-results table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def wait_for_dynamodb(client: BaseClient, *, attempts: int = 20, delay: float = 0.25) -> None:
    """Allow a newly started local container a short bounded startup window."""
    for attempt in range(1, attempts + 1):
        try:
            client.list_tables(Limit=1)
            return
        except (BotoCoreError, ClientError):
            if attempt == attempts:
                raise
            time.sleep(delay)


def create_product_classification_results_table() -> bool:
    """Create the product-classification composite result table idempotently."""
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise RuntimeError("DYNAMODB_ENDPOINT_URL is required for local table creation")
    client = create_dynamodb_client(settings)
    wait_for_dynamodb(client)
    table_name = settings.table_name("product-classification-results")
    created = False
    try:
        client.create_table(
            TableName=table_name,
            AttributeDefinitions=[
                {"AttributeName": "classificationId", "AttributeType": "S"},
                {"AttributeName": "recordKey", "AttributeType": "S"},
                {"AttributeName": "jobId", "AttributeType": "S"},
                {"AttributeName": "createdAt", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "classificationId", "KeyType": "HASH"},
                {"AttributeName": "recordKey", "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": JOB_ID_INDEX,
                    "KeySchema": [
                        {"AttributeName": "jobId", "KeyType": "HASH"},
                        {"AttributeName": "createdAt", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        created = True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise
    client.get_waiter("table_exists").wait(TableName=table_name)
    logger.info(
        "Product-classification-results table %s is %s",
        table_name,
        "created" if created else "already present",
    )
    return created


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    create_products_table()
    create_sources_table()
    create_processing_jobs_table()
    create_extraction_results_table()
    create_table_extraction_results_table()
    create_csv_processing_results_table()
    create_image_analysis_results_table()
    create_image_ocr_results_table()
    create_product_classification_results_table()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
