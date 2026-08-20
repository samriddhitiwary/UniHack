"""SPEC-035 deterministic Product Intelligence Score coverage."""

# mypy: disable-error-code="no-untyped-def,no-untyped-call,arg-type,unused-ignore"

from dataclasses import FrozenInstanceError, replace
from typing import Any, cast
from uuid import uuid4

import pytest
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.core.exceptions import (
    InvalidProductIntelligenceCursorError,
    ProductIntelligenceAlreadyExistsError,
    ProductIntelligenceEnrichmentMismatchError,
)
from app.domain.catalog_projection import CatalogBlockingReason, CatalogProjectionStatus
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_intelligence import (
    ComponentEvaluationStatus,
    ProductIntelligenceComponent,
    ProductIntelligenceComponentScore,
    ProductIntelligenceGrade,
)
from app.repositories.dynamodb_product_intelligence import (
    DynamoDBProductIntelligenceScoreRepository,
    product_intelligence_input_key,
)
from app.services.catalog_product_identity_projector import CatalogProductIdentityProjector
from app.services.catalog_projection_engine import CatalogProjectionEngine
from app.services.catalog_publishing_readiness import CatalogPublishingReadinessEvaluator
from app.services.catalog_reviewed_attribute_projector import CatalogReviewedAttributeProjector
from app.services.product_intelligence_ai_scorer import ProductIntelligenceAiScorer
from app.services.product_intelligence_engine import ProductIntelligenceEngine
from app.services.product_intelligence_score import ProductIntelligenceScoreService
from app.services.product_intelligence_score_calculator import ProductIntelligenceScoreCalculator
from app.services.reviewed_attribute_materialization_engine import (
    ReviewedAttributeMaterializationEngine,
)
from app.utils.dynamodb import deserialize_item
from tests.fixtures.attribute_normalization import NOW
from tests.fixtures.catalog_enrichment import FakeLlm, enrichment_projection, grounded_response
from tests.fixtures.catalog_projection import catalog_product
from tests.fixtures.reviewed_attributes import completed_review
from tests.unit.test_catalog_enrichment_engine import engine as enrichment_engine
from tests.unit.test_catalog_enrichment_engine import generate


def coherent_pipeline(*, manual=False, warning=False, conflict=False):
    schema, normalization, conflicts, validation, completeness, selection, review, decisions, _ = (
        completed_review(manual_voltage=manual, warning_power=warning, conflict_voltage=conflict)
    )
    materialization = ReviewedAttributeMaterializationEngine().materialize(
        job_id=uuid4(),
        review=review,
        current_decisions=decisions,
        schema=schema,
        selection_result=selection,
        validation_result=validation,
        normalization_result=normalization,
        now=NOW,
    )
    product = catalog_product(materialization)
    projection = CatalogProjectionEngine(
        identity_projector=CatalogProductIdentityProjector(),
        attribute_projector=CatalogReviewedAttributeProjector(),
        readiness_evaluator=CatalogPublishingReadinessEvaluator(),
    ).project(job_id=uuid4(), product=product, materialization=materialization, now=NOW)
    return projection, completeness, validation, conflicts, selection, review, materialization


def score_result(**options):
    inputs = coherent_pipeline(**options)
    return ProductIntelligenceEngine().evaluate(
        score_id=uuid4(),
        job_id=uuid4(),
        projection=inputs[0],
        completeness=inputs[1],
        validation=inputs[2],
        conflicts=inputs[3],
        selection=inputs[4],
        review=inputs[5],
        materialization=inputs[6],
        enrichment=None,
        created_at=NOW,
    )


def component(raw: int, kind: ProductIntelligenceComponent) -> ProductIntelligenceComponentScore:
    weights = dict(
        zip(ProductIntelligenceComponent, (2500, 2000, 2000, 1500, 1000, 1000), strict=True)
    )
    return ProductIntelligenceComponentScore(
        component=kind,
        status=ComponentEvaluationStatus.EVALUATED,
        raw_score_bp=raw,
        base_weight_bp=weights[kind],
        normalized_weight_bp=0,
        weighted_contribution_bp=0,
        strength_codes=(),
        improvement_codes=(),
        metrics=(),
    )


def test_perfect_score_and_grade_boundaries_are_exact_integer_arithmetic() -> None:
    calculator = ProductIntelligenceScoreCalculator()
    values, score, grade = calculator.calculate(
        tuple(component(10_000, kind) for kind in ProductIntelligenceComponent)
    )
    assert score == 10_000 and grade is ProductIntelligenceGrade.EXCELLENT
    assert sum(item.normalized_weight_bp for item in values) == 10_000
    assert sum(item.weighted_contribution_bp for item in values) == score
    expected = {
        9000: ProductIntelligenceGrade.EXCELLENT,
        8000: ProductIntelligenceGrade.GOOD,
        6500: ProductIntelligenceGrade.FAIR,
        5000: ProductIntelligenceGrade.POOR,
        4999: ProductIntelligenceGrade.CRITICAL,
    }
    assert {value: calculator.grade(value) for value in expected} == expected


def test_missing_ai_is_not_evaluated_and_does_not_reduce_perfect_score() -> None:
    values = tuple(component(10_000, kind) for kind in ProductIntelligenceComponent)
    values = (*values[:-1], ProductIntelligenceAiScorer().score(None))
    normalized, score, _ = ProductIntelligenceScoreCalculator().calculate(values)
    assert score == 10_000
    assert normalized[-1].status is ComponentEvaluationStatus.NOT_EVALUATED
    assert normalized[-1].normalized_weight_bp == 0
    assert "AI_ENRICHMENT_NOT_EVALUATED" in normalized[-1].improvement_codes


def test_ai_formula_uses_grounding_and_coverage_only() -> None:
    _, _, projection = enrichment_projection()
    enrichment = generate(enrichment_engine(FakeLlm([grounded_response(projection)])), projection)
    actual = ProductIntelligenceAiScorer().score(enrichment)
    assert (
        actual.raw_score_bp
        == (enrichment.grounding_score_bp * 8000 + enrichment.fact_coverage_bp * 2000) // 10_000
    )
    inputs = coherent_pipeline()
    with pytest.raises(ProductIntelligenceEnrichmentMismatchError):
        ProductIntelligenceEngine().evaluate(
            score_id=uuid4(),
            job_id=uuid4(),
            projection=inputs[0],
            completeness=inputs[1],
            validation=inputs[2],
            conflicts=inputs[3],
            selection=inputs[4],
            review=inputs[5],
            materialization=inputs[6],
            enrichment=enrichment,
            created_at=NOW,
        )


def test_engine_preserves_lineage_is_deterministic_and_explainable() -> None:
    first = score_result(manual=True, warning=True, conflict=True)
    inputs = coherent_pipeline(manual=True, warning=True, conflict=True)
    second = ProductIntelligenceEngine().evaluate(
        score_id=first.score_id,
        job_id=first.job_id,
        projection=inputs[0],
        completeness=inputs[1],
        validation=inputs[2],
        conflicts=inputs[3],
        selection=inputs[4],
        review=inputs[5],
        materialization=inputs[6],
        enrichment=None,
        created_at=NOW,
    )
    assert first.overall_score_bp == second.overall_score_bp
    assert first.projection_id != second.projection_id
    assert len(first.components) == 6 and len(first.top_improvement_codes) <= 5
    assert "REDUCE_SOURCE_CONFLICTS" in first.improvement_codes
    assert "REDUCE_MANUAL_OVERRIDES" in first.improvement_codes
    with pytest.raises(FrozenInstanceError):
        first.overall_score_bp = 0  # type: ignore[misc]


def test_required_dominance_warning_and_distinct_source_formulas() -> None:
    result = score_result(warning=True)
    by_kind = {item.component: item for item in result.components}
    assert by_kind[ProductIntelligenceComponent.VALIDATION_QUALITY].raw_score_bp < 10_000
    assert by_kind[ProductIntelligenceComponent.SOURCE_CORROBORATION].raw_score_bp == 9_000
    assert by_kind[ProductIntelligenceComponent.COMPLETENESS].raw_score_bp == 8_500
    assert "IMPROVE_OPTIONAL_ATTRIBUTE_COVERAGE" in result.improvement_codes


def test_structurally_coherent_blocked_projection_is_scored_without_readiness_override() -> None:
    inputs = coherent_pipeline()
    blocked = replace(
        inputs[0],
        status=CatalogProjectionStatus.BLOCKED,
        blocking_reason_codes=(CatalogBlockingReason.PRODUCT_NAME_MISSING,),
        warning_reason_codes=(),
    )
    result = ProductIntelligenceEngine().evaluate(
        score_id=uuid4(),
        job_id=uuid4(),
        projection=blocked,
        completeness=inputs[1],
        validation=inputs[2],
        conflicts=inputs[3],
        selection=inputs[4],
        review=inputs[5],
        materialization=inputs[6],
        enrichment=None,
        created_at=NOW,
    )
    assert result.projection_status is CatalogProjectionStatus.BLOCKED
    assert result.overall_score_bp > 0


class MemoryDynamo:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}

    def transact_write_items(self, *, TransactItems):
        decoded = [deserialize_item(item["Put"]["Item"]) for item in TransactItems]
        keys = [(str(item["scoreId"]), str(item["recordKey"])) for item in decoded]
        if any(key in self.items for key in keys):
            raise ClientError(
                {"Error": {"Code": "TransactionCanceledException"}}, "TransactWriteItems"
            )
        for raw, item in zip(TransactItems, decoded, strict=True):
            self.items[(str(item["scoreId"]), str(item["recordKey"]))] = raw["Put"]["Item"]
        return {}

    def query(self, **request):
        wanted = str(next(iter(deserialize_item(request["ExpressionAttributeValues"]).values())))
        if "IndexName" in request:
            field = {
                "JobIdIndex": "jobId",
                "ProductCreatedAtIndex": "productId",
                "ProjectionIdIndex": "projectionId",
            }[request["IndexName"]]
            items = [
                item
                for item in self.items.values()
                if str(deserialize_item(item).get(field, "")) == wanted
            ]
            return {"Items": items[: request["Limit"]]}
        return {
            "Items": [item for (partition, _), item in self.items.items() if partition == wanted]
        }

    def get_item(self, *, Key, **kwargs):
        key = deserialize_item(Key)
        item = self.items.get((str(key["scoreId"]), str(key["recordKey"])))
        return {"Item": item} if item else {}


def test_repository_round_trip_indexes_history_and_exact_input_guard() -> None:
    result = score_result()
    client = MemoryDynamo()
    repository = DynamoDBProductIntelligenceScoreRepository(cast(BaseClient, client), "scores")
    assert repository.create(result) == result
    assert repository.get_by_id(result.score_id) == result
    assert repository.get_by_job_id(result.job_id) == result
    assert repository.get_by_projection_id(result.projection_id) == (result,)
    key = product_intelligence_input_key(result.projection_id, None, result.policy_version)
    assert repository.get_by_input_key(key) == result
    assert repository.list_by_product(result.product_id, limit=10).items == (result,)
    with pytest.raises(ProductIntelligenceAlreadyExistsError):
        repository.create(replace(result, score_id=uuid4(), job_id=uuid4()))


def test_score_history_cursor_is_malformed_and_product_scoped() -> None:
    product_id = uuid4()
    with pytest.raises(InvalidProductIntelligenceCursorError):
        DynamoDBProductIntelligenceScoreRepository._decode_cursor("not-base64!", product_id)
    cursor = DynamoDBProductIntelligenceScoreRepository._encode_cursor(
        {"scoreId": {"S": str(uuid4())}}, product_id
    )
    with pytest.raises(InvalidProductIntelligenceCursorError):
        DynamoDBProductIntelligenceScoreRepository._decode_cursor(cursor, uuid4())


class SingleRepository:
    def __init__(self, item=None, events=None, name="repo") -> None:
        self.item, self.events, self.name = item, events if events is not None else [], name

    def get_by_id(self, identifier):
        return (
            self.item if self.item is not None and identifier in vars_for_ids(self.item) else None
        )

    def get_by_input_key(self, key):
        return None

    def create(self, item):
        self.events.append("result-created")
        self.item = item
        return item


def vars_for_ids(item):
    return {
        value
        for name in dir(item)
        if name.endswith("_id") and isinstance((value := getattr(item, name)), type(uuid4()))
    }


class JobRepository(SingleRepository):
    def update(self, item, *, expected_version):
        assert self.item.version == expected_version
        self.events.append(f"job-{item.status.value.lower()}")
        self.item = item
        return item


def test_service_validates_then_runs_persists_and_completes() -> None:
    projection, completeness, validation, conflicts, selection, review, materialization = (
        coherent_pipeline()
    )
    product = catalog_product(materialization)
    job = ProcessingJob.create(
        product_id=product.product_id,
        source_id=None,
        job_type=ProcessingJobType.PRODUCT_INTELLIGENCE_SCORE,
        projection_id=projection.projection_id,
        now=NOW,
    )
    events: list[str] = []
    jobs, results = JobRepository(job, events), SingleRepository(events=events)
    service = ProductIntelligenceScoreService(
        job_repository=jobs,
        product_repository=SingleRepository(product),
        projection_repository=SingleRepository(projection),
        completeness_repository=SingleRepository(completeness),
        validation_repository=SingleRepository(validation),
        conflict_repository=SingleRepository(conflicts),
        selection_repository=SingleRepository(selection),
        review_repository=SingleRepository(review),
        materialization_repository=SingleRepository(materialization),
        enrichment_repository=SingleRepository(),
        result_repository=results,
        engine=ProductIntelligenceEngine(),
        clock=lambda: NOW,
    )
    actual = service.score_for_job(job_id=job.job_id)
    assert actual.projection_id == projection.projection_id
    assert events == ["job-running", "result-created", "job-completed"]
    assert jobs.item.status is ProcessingJobStatus.COMPLETED
    assert jobs.item.result_reference == f"product-intelligence-score-results/{actual.score_id}"
