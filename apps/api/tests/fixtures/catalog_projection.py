"""Commerce catalog projection fixtures built from completed SPEC-030 artifacts."""

from dataclasses import replace
from uuid import uuid4

from app.domain.processing_jobs import ProcessingJob, ProcessingJobType
from app.domain.products import Product, ProductCategory, ProductStatus
from app.services.catalog_product_identity_projector import CatalogProductIdentityProjector
from app.services.catalog_projection_engine import CatalogProjectionEngine
from app.services.catalog_publishing_readiness import CatalogPublishingReadinessEvaluator
from app.services.catalog_reviewed_attribute_projector import CatalogReviewedAttributeProjector
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.reviewed_attributes import completed_pump_review, completed_review


def reviewed_materialization(*, pump=False, manual=False, warning=False, clean=True):
    pipeline = (
        completed_pump_review()
        if pump
        else completed_review(manual_voltage=manual, warning_power=warning)
    )
    schema, normalization, _, validation, _, selection, review, decisions, _ = pipeline
    result = ReviewedAttributeMaterializationEngine().materialize(
        job_id=uuid4(),
        review=review,
        current_decisions=decisions,
        schema=schema,
        selection_result=selection,
        validation_result=validation,
        normalization_result=normalization,
        now=NOW,
    )
    return (
        replace(result, optional_attribute_count=0, unresolved_optional_count=0)
        if clean
        else result
    )


def catalog_product(materialization, **changes):
    product = Product.create(
        name="Industrial Pump"
        if materialization.category is ProductCategory.CENTRIFUGAL_PUMP
        else "Industrial Motor",
        manufacturer="CatalogIQ Manufacturing",
        model_number="CAT-100",
        category=materialization.category,
        description="Reviewed industrial equipment",
        now=NOW,
    )
    return replace(
        product,
        product_id=materialization.product_id,
        status=ProductStatus.REVIEW_REQUIRED,
        version=3,
        **changes,
    )


def projection_engine() -> CatalogProjectionEngine:
    return CatalogProjectionEngine(
        identity_projector=CatalogProductIdentityProjector(),
        attribute_projector=CatalogReviewedAttributeProjector(),
        readiness_evaluator=CatalogPublishingReadinessEvaluator(),
    )


def projected_result(*, pump=False, manual=False, warning=False, clean=True, **product_changes):
    materialization = reviewed_materialization(
        pump=pump, manual=manual, warning=warning, clean=clean
    )
    product = catalog_product(materialization, **product_changes)
    result = projection_engine().project(
        job_id=uuid4(), product=product, materialization=materialization, now=NOW
    )
    return product, materialization, result


def catalog_job(materialization) -> ProcessingJob:
    return ProcessingJob.create(
        product_id=materialization.product_id,
        source_id=None,
        job_type=ProcessingJobType.CATALOG_PROJECTION,
        reviewed_attribute_materialization_id=materialization.materialization_id,
        now=NOW,
    )
