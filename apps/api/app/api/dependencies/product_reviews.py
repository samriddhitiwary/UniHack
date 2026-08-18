"""Product-review repository and service dependency providers."""

from typing import Annotated

from botocore.client import BaseClient
from fastapi import Depends

from app.api.dependencies.dynamodb import get_dynamodb_client
from app.api.dependencies.products import get_product_repository
from app.core.config import Settings, get_settings
from app.repositories.dynamodb_attribute_completeness import (
    DynamoDBAttributeCompletenessResultRepository,
)
from app.repositories.dynamodb_attribute_conflicts import (
    DynamoDBAttributeConflictDetectionResultRepository,
)
from app.repositories.dynamodb_attribute_normalization import (
    DynamoDBAttributeNormalizationResultRepository,
)
from app.repositories.dynamodb_attribute_selection import DynamoDBAttributeSelectionResultRepository
from app.repositories.dynamodb_attribute_validation import (
    DynamoDBAttributeValidationResultRepository,
)
from app.repositories.dynamodb_category_schemas import DynamoDBCategoryAttributeSchemaRepository
from app.repositories.dynamodb_product_review import DynamoDBProductReviewRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.products import ProductRepository
from app.services.product_review import ProductReviewService
from app.services.review_manual_override import ReviewManualOverride


def get_product_review_repository(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ProductReviewRepository:
    return DynamoDBProductReviewRepository(client, settings.table_name("product-reviews"))


def get_product_review_service(
    client: Annotated[BaseClient, Depends(get_dynamodb_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    products: Annotated[ProductRepository, Depends(get_product_repository)],
    reviews: Annotated[ProductReviewRepository, Depends(get_product_review_repository)],
) -> ProductReviewService:
    return ProductReviewService(
        product_repository=products,
        selection_repository=DynamoDBAttributeSelectionResultRepository(
            client, settings.table_name("attribute-selection-results")
        ),
        conflict_repository=DynamoDBAttributeConflictDetectionResultRepository(
            client, settings.table_name("attribute-conflict-detection-results")
        ),
        validation_repository=DynamoDBAttributeValidationResultRepository(
            client, settings.table_name("attribute-validation-results")
        ),
        completeness_repository=DynamoDBAttributeCompletenessResultRepository(
            client, settings.table_name("attribute-completeness-results")
        ),
        normalization_repository=DynamoDBAttributeNormalizationResultRepository(
            client, settings.table_name("attribute-normalization-results")
        ),
        schema_repository=DynamoDBCategoryAttributeSchemaRepository(
            client, settings.table_name("category-attribute-schemas")
        ),
        review_repository=reviews,
        manual_override=ReviewManualOverride(
            max_value_characters=settings.review_max_manual_value_characters
        ),
        max_decisions=settings.review_max_decisions,
        max_attributes=settings.review_max_attributes,
    )
