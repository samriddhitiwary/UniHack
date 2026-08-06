"""Real DynamoDB Local contract smoke test for the product repository."""

import os
from contextlib import suppress
from dataclasses import replace
from datetime import timedelta

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.core.exceptions import (
    ProductAlreadyExistsError,
    ProductNotFoundError,
    ProductVersionConflictError,
)
from app.domain.products import Product, ProductStatus
from app.repositories.dynamodb_products import DynamoDBProductRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating the local products table",
)


def test_product_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    repository = DynamoDBProductRepository(
        create_dynamodb_client(settings), settings.table_name("products")
    )
    product = Product.create(name="SPEC-002 Integration Product")

    try:
        assert repository.create(product) == product
        with pytest.raises(ProductAlreadyExistsError):
            repository.create(product)
        assert repository.get_by_id(product.product_id) == product

        attempted = replace(product, created_at=product.created_at - timedelta(days=1))
        updated = repository.update(attempted, expected_version=1)
        assert updated.version == 2
        assert updated.updated_at >= product.updated_at
        assert updated.created_at == product.created_at
        with pytest.raises(ProductVersionConflictError):
            repository.update(product, expected_version=1)

        all_products = repository.list_products(limit=100)
        assert updated.product_id in {item.product_id for item in all_products.items}
        draft_products = repository.list_by_status(ProductStatus.DRAFT, limit=100)
        assert updated.product_id in {item.product_id for item in draft_products.items}

        repository.delete(product.product_id)
        assert repository.get_by_id(product.product_id) is None
        with pytest.raises(ProductNotFoundError):
            repository.delete(product.product_id)
    finally:
        with suppress(ProductNotFoundError):
            repository.delete(product.product_id)
