"""Opt-in DynamoDB Local contract test for product-source persistence."""

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.core.exceptions import ProductSourceVersionConflictError
from app.domain.product_sources import ProductSource, ProductSourceStatus, ProductSourceType
from app.repositories.dynamodb_product_sources import DynamoDBProductSourceRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating the local source table",
)


def test_product_source_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    repository = DynamoDBProductSourceRepository(
        create_dynamodb_client(settings), settings.table_name("sources")
    )
    product_id = uuid4()
    first_time = datetime.now(UTC) - timedelta(seconds=1)
    first = ProductSource.create(
        product_id=product_id,
        source_type=ProductSourceType.PDF,
        original_filename="first.pdf",
        mime_type="application/pdf",
        now=first_time,
    )
    second = ProductSource.create(
        product_id=product_id,
        source_type=ProductSourceType.TEXT,
        text_content="second",
        now=first_time + timedelta(seconds=1),
    )
    try:
        repository.create(first)
        repository.create(second)
        assert repository.get_by_id(product_id, first.source_id) == first
        page = repository.list_by_product(product_id)
        assert [source.source_id for source in page.items] == [second.source_id, first.source_id]

        updated = repository.update(
            replace(first, status=ProductSourceStatus.READY), expected_version=1
        )
        assert updated.version == 2
        with pytest.raises(ProductSourceVersionConflictError):
            repository.update(first, expected_version=1)
        repository.delete(product_id, first.source_id, expected_version=2)
        assert repository.get_by_id(product_id, first.source_id) is None
    finally:
        for source_id in (first.source_id, second.source_id):
            current = repository.get_by_id(product_id, source_id)
            if current is not None:
                repository.delete(product_id, source_id, current.version)
