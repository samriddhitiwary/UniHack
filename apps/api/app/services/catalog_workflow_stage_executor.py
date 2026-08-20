"""Adapters from workflow stages to the existing synchronous application services."""

from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any, Protocol, cast
from uuid import UUID

from app.core.exceptions import CatalogWorkflowReviewNotCompletedError
from app.domain.catalog_projection import CatalogProjectionStatus
from app.domain.catalog_workflow import (
    CatalogIntelligenceWorkflow,
    CatalogWorkflowSkipReason,
    CatalogWorkflowStageName,
    CatalogWorkflowStageOutcome,
    CatalogWorkflowStageStatus,
)
from app.domain.processing_jobs import ProcessingJob, ProcessingJobStatus, ProcessingJobType
from app.domain.product_classification import ProductClassificationStatus
from app.domain.product_review import ProductReviewSessionStatus
from app.domain.products import ProductStatus
from app.repositories.catalog_projection import CommerceCatalogProjectionRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_review import ProductReviewRepository
from app.repositories.products import ProductRepository
from app.services.catalog_workflow_planner import CatalogWorkflowPlanner
from app.services.product_review import ProductReviewService
from app.services.publishing_readiness_application import PublishingReadinessApplicationService


class StageRunner(Protocol):
    def __call__(self, *, job_id: UUID) -> object: ...


ResultLoader = Callable[[UUID], object | None]

_STAGE_JOB_TYPES = {
    CatalogWorkflowStageName.PRODUCT_CLASSIFICATION: ProcessingJobType.PRODUCT_CLASSIFICATION,
    CatalogWorkflowStageName.ATTRIBUTE_EXTRACTION: ProcessingJobType.ATTRIBUTE_EXTRACTION,
    CatalogWorkflowStageName.ATTRIBUTE_NORMALIZATION: ProcessingJobType.ATTRIBUTE_NORMALIZATION,
    CatalogWorkflowStageName.CONFLICT_DETECTION: ProcessingJobType.ATTRIBUTE_CONFLICT_DETECTION,
    CatalogWorkflowStageName.COMPLETENESS: ProcessingJobType.ATTRIBUTE_COMPLETENESS,
    CatalogWorkflowStageName.ATTRIBUTE_VALIDATION: ProcessingJobType.ATTRIBUTE_VALIDATION,
    CatalogWorkflowStageName.ATTRIBUTE_SELECTION: ProcessingJobType.ATTRIBUTE_SELECTION,
    CatalogWorkflowStageName.REVIEWED_ATTRIBUTE_MATERIALIZATION: (
        ProcessingJobType.REVIEWED_ATTRIBUTE_MATERIALIZATION
    ),
    CatalogWorkflowStageName.CATALOG_PROJECTION: ProcessingJobType.CATALOG_PROJECTION,
    CatalogWorkflowStageName.CATALOG_EXPORT: ProcessingJobType.CATALOG_EXPORT,
    CatalogWorkflowStageName.AI_ENRICHMENT: ProcessingJobType.AI_CATALOG_ENRICHMENT,
    CatalogWorkflowStageName.PRODUCT_INTELLIGENCE_SCORE: (
        ProcessingJobType.PRODUCT_INTELLIGENCE_SCORE
    ),
}

_RESULT_IDS = {
    CatalogWorkflowStageName.PRODUCT_CLASSIFICATION: ("classification_id", "classification_id"),
    CatalogWorkflowStageName.ATTRIBUTE_EXTRACTION: ("extraction_id", "extraction_id"),
    CatalogWorkflowStageName.ATTRIBUTE_NORMALIZATION: ("normalization_id", "normalization_id"),
    CatalogWorkflowStageName.CONFLICT_DETECTION: (
        "conflict_detection_id",
        "conflict_detection_id",
    ),
    CatalogWorkflowStageName.COMPLETENESS: ("completeness_id", "completeness_id"),
    CatalogWorkflowStageName.ATTRIBUTE_VALIDATION: ("validation_id", "validation_id"),
    CatalogWorkflowStageName.ATTRIBUTE_SELECTION: ("selection_id", "selection_id"),
    CatalogWorkflowStageName.REVIEWED_ATTRIBUTE_MATERIALIZATION: (
        "materialization_id",
        "materialization_id",
    ),
    CatalogWorkflowStageName.CATALOG_PROJECTION: ("projection_id", "projection_id"),
    CatalogWorkflowStageName.CATALOG_EXPORT: ("export_id", "export_id"),
    CatalogWorkflowStageName.AI_ENRICHMENT: ("enrichment_id", "enrichment_id"),
    CatalogWorkflowStageName.PRODUCT_INTELLIGENCE_SCORE: ("score_id", "score_id"),
}


class WorkflowClassificationUnresolvedError(Exception):
    code = "WORKFLOW_CLASSIFICATION_UNRESOLVED"
    safe_message = "Product classification did not resolve to one supported category."


class ExistingServicesCatalogWorkflowStageExecutor:
    """Create lineage-bound jobs, then invoke the existing service for each job type."""

    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        review_repository: ProductReviewRepository,
        projection_repository: CommerceCatalogProjectionRepository,
        review_service: ProductReviewService,
        readiness_service: PublishingReadinessApplicationService,
        runners: Mapping[ProcessingJobType, StageRunner],
        result_loaders: Mapping[ProcessingJobType, ResultLoader],
        planner: CatalogWorkflowPlanner | None = None,
    ) -> None:
        required = set(ProcessingJobType) - {ProcessingJobType.SOURCE_PROCESSING}
        if not required.issubset(runners):
            raise ValueError("all existing processing-job services must be registered")
        if not required.issubset(result_loaders):
            raise ValueError("all existing processing-job result loaders must be registered")
        self._jobs = job_repository
        self._products = product_repository
        self._reviews = review_repository
        self._projections = projection_repository
        self._review_service = review_service
        self._readiness = readiness_service
        self._runners = dict(runners)
        self._result_loaders = dict(result_loaders)
        self._planner = planner or CatalogWorkflowPlanner()

    def execute(
        self,
        stage: CatalogWorkflowStageName,
        workflow: CatalogIntelligenceWorkflow,
    ) -> CatalogWorkflowStageOutcome:
        if stage is CatalogWorkflowStageName.SOURCE_PROCESSING:
            return self._source_processing(workflow)
        if stage is CatalogWorkflowStageName.HUMAN_REVIEW:
            return self._human_review(workflow)
        if stage is CatalogWorkflowStageName.PUBLISHING_READINESS:
            return self._publishing_readiness(workflow)
        skipped = self._optional_skip(stage, workflow)
        if skipped is not None:
            return skipped
        job_type = _STAGE_JOB_TYPES[stage]
        job = self._find_compatible_job(workflow, job_type)
        if job is None:
            job = self._jobs.create(self._new_job(workflow, job_type))
            result = self._runners[job_type](job_id=job.job_id)
        else:
            result = self._result_loaders[job_type](job.job_id)
            if result is None:
                raise ValueError("completed job result no longer exists")
        if (
            stage is CatalogWorkflowStageName.PRODUCT_CLASSIFICATION
            and getattr(result, "status", None) is not ProductClassificationStatus.CLASSIFIED
        ):
            raise WorkflowClassificationUnresolvedError()
        field, result_attr = _RESULT_IDS[stage]
        result_id = UUID(str(getattr(result, result_attr)))
        return CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.COMPLETED,
            job_id=job.job_id,
            result_reference=self._completed_reference(job),
            **cast(Any, {field: result_id}),
        )

    def review_is_completed(self, workflow: CatalogIntelligenceWorkflow) -> bool:
        if workflow.review_id is None:
            return False
        review = self._reviews.get_by_id(workflow.review_id)
        return (
            review is not None
            and review.product_id == workflow.product_id
            and review.selection_id == workflow.selection_id
            and review.status is ProductReviewSessionStatus.COMPLETED
        )

    def completion_has_warnings(self, workflow: CatalogIntelligenceWorkflow) -> bool:
        if workflow.projection_id is None:
            return False
        projection = self._projections.get_by_id(workflow.projection_id)
        return projection is not None and projection.status in {
            CatalogProjectionStatus.BLOCKED,
            CatalogProjectionStatus.READY_WITH_WARNINGS,
        }

    def _source_processing(
        self, workflow: CatalogIntelligenceWorkflow
    ) -> CatalogWorkflowStageOutcome:
        child_ids: list[UUID] = []
        for plan in self._planner.plan_sources(workflow.source_snapshot):
            for job_type in plan.job_types:
                job = self._find_source_job(workflow.product_id, plan.source_id, job_type)
                if job is None:
                    job = self._jobs.create(
                        ProcessingJob.create(
                            product_id=workflow.product_id,
                            source_id=plan.source_id,
                            job_type=job_type,
                        )
                    )
                    self._runners[job_type](job_id=job.job_id)
                elif self._result_loaders[job_type](job.job_id) is None:
                    raise ValueError("completed source job result no longer exists")
                child_ids.append(job.job_id)
        return CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.COMPLETED,
            child_job_ids=tuple(child_ids),
            result_reference=f"catalog-workflows/{workflow.workflow_id}/sources",
        )

    def _human_review(self, workflow: CatalogIntelligenceWorkflow) -> CatalogWorkflowStageOutcome:
        if workflow.selection_id is None:
            raise ValueError("selection lineage is missing")
        review = self._reviews.get_by_selection_id(workflow.selection_id)
        if review is None:
            review = self._review_service.create_review(
                product_id=workflow.product_id,
                selection_id=workflow.selection_id,
            )
        if review.product_id != workflow.product_id:
            raise CatalogWorkflowReviewNotCompletedError()
        if review.status is ProductReviewSessionStatus.COMPLETED:
            product = self._products.get_by_id(workflow.product_id)
            if product is None:
                raise ValueError("Product no longer exists")
            return CatalogWorkflowStageOutcome(
                status=CatalogWorkflowStageStatus.COMPLETED,
                review_id=review.review_id,
                result_reference=f"product-reviews/{review.review_id}",
                product_version=product.version,
            )
        product = self._products.get_by_id(workflow.product_id)
        if product is None:
            raise ValueError("Product no longer exists")
        if product.status is not ProductStatus.REVIEW_REQUIRED:
            product = self._products.update(
                replace(product, status=ProductStatus.REVIEW_REQUIRED),
                expected_version=product.version,
            )
        return CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.WAITING,
            review_id=review.review_id,
            result_reference=f"product-reviews/{review.review_id}",
            product_version=product.version,
        )

    def _publishing_readiness(
        self, workflow: CatalogIntelligenceWorkflow
    ) -> CatalogWorkflowStageOutcome:
        if not workflow.configuration.apply_publishing_readiness:
            return self._skip(CatalogWorkflowSkipReason.DISABLED)
        if workflow.projection_id is None:
            raise ValueError("projection lineage is missing")
        projection = self._projections.get_by_id(workflow.projection_id)
        if projection is None:
            raise ValueError("projection no longer exists")
        if projection.status is CatalogProjectionStatus.BLOCKED:
            return self._skip(CatalogWorkflowSkipReason.PROJECTION_BLOCKED)
        product = self._products.get_by_id(workflow.product_id)
        if product is None:
            raise ValueError("Product no longer exists")
        if product.status is ProductStatus.READY_TO_PUBLISH:
            return self._skip(CatalogWorkflowSkipReason.ALREADY_READY_TO_PUBLISH)
        self._readiness.apply(
            product_id=workflow.product_id,
            projection_id=workflow.projection_id,
            expected_version=product.version,
        )
        return CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.COMPLETED,
            result_reference=f"catalog-projection-results/{workflow.projection_id}/readiness",
        )

    def _optional_skip(
        self,
        stage: CatalogWorkflowStageName,
        workflow: CatalogIntelligenceWorkflow,
    ) -> CatalogWorkflowStageOutcome | None:
        enabled = {
            CatalogWorkflowStageName.CATALOG_EXPORT: workflow.configuration.generate_export,
            CatalogWorkflowStageName.AI_ENRICHMENT: (workflow.configuration.generate_ai_enrichment),
            CatalogWorkflowStageName.PRODUCT_INTELLIGENCE_SCORE: (
                workflow.configuration.calculate_intelligence_score
            ),
        }.get(stage)
        if enabled is False:
            return self._skip(CatalogWorkflowSkipReason.DISABLED)
        if (
            stage
            in {
                CatalogWorkflowStageName.CATALOG_EXPORT,
                CatalogWorkflowStageName.AI_ENRICHMENT,
            }
            and workflow.projection_id is not None
        ):
            projection = self._projections.get_by_id(workflow.projection_id)
            if projection is not None and projection.status is CatalogProjectionStatus.BLOCKED:
                return self._skip(CatalogWorkflowSkipReason.PROJECTION_BLOCKED)
        return None

    @staticmethod
    def _skip(reason: CatalogWorkflowSkipReason) -> CatalogWorkflowStageOutcome:
        return CatalogWorkflowStageOutcome(
            status=CatalogWorkflowStageStatus.SKIPPED,
            skip_reason=reason.value,
        )

    def _new_job(
        self, workflow: CatalogIntelligenceWorkflow, job_type: ProcessingJobType
    ) -> ProcessingJob:
        kwargs: dict[str, Any] = {}
        lineage = {
            ProcessingJobType.ATTRIBUTE_EXTRACTION: (
                "classification_id",
                workflow.classification_id,
            ),
            ProcessingJobType.ATTRIBUTE_NORMALIZATION: (
                "attribute_extraction_id",
                workflow.extraction_id,
            ),
            ProcessingJobType.ATTRIBUTE_CONFLICT_DETECTION: (
                "attribute_normalization_id",
                workflow.normalization_id,
            ),
            ProcessingJobType.ATTRIBUTE_COMPLETENESS: (
                "attribute_conflict_detection_id",
                workflow.conflict_detection_id,
            ),
            ProcessingJobType.REVIEWED_ATTRIBUTE_MATERIALIZATION: (
                "review_id",
                workflow.review_id,
            ),
            ProcessingJobType.CATALOG_PROJECTION: (
                "reviewed_attribute_materialization_id",
                workflow.materialization_id,
            ),
            ProcessingJobType.CATALOG_EXPORT: ("projection_id", workflow.projection_id),
            ProcessingJobType.AI_CATALOG_ENRICHMENT: ("projection_id", workflow.projection_id),
        }
        if job_type in lineage:
            name, value = lineage[job_type]
            kwargs[name] = value
        if job_type is ProcessingJobType.ATTRIBUTE_VALIDATION:
            kwargs["attribute_normalization_id"] = workflow.normalization_id
        if job_type is ProcessingJobType.ATTRIBUTE_SELECTION:
            kwargs.update(
                attribute_normalization_id=workflow.normalization_id,
                attribute_conflict_detection_id=workflow.conflict_detection_id,
                attribute_validation_id=workflow.validation_id,
                attribute_completeness_id=workflow.completeness_id,
            )
        if job_type is ProcessingJobType.PRODUCT_INTELLIGENCE_SCORE:
            kwargs.update(
                projection_id=workflow.projection_id,
                enrichment_id=workflow.enrichment_id,
            )
        return ProcessingJob.create(
            product_id=workflow.product_id,
            source_id=None,
            job_type=job_type,
            **kwargs,
        )

    def _find_source_job(
        self, product_id: UUID, source_id: UUID, job_type: ProcessingJobType
    ) -> ProcessingJob | None:
        cursor: str | None = None
        while True:
            page = self._jobs.list_by_source(product_id, source_id, limit=100, cursor=cursor)
            for job in page.items:
                if self._reusable(job, job_type):
                    return job
            cursor = page.next_cursor
            if cursor is None:
                return None

    def _find_compatible_job(
        self, workflow: CatalogIntelligenceWorkflow, job_type: ProcessingJobType
    ) -> ProcessingJob | None:
        expected = self._new_job(workflow, job_type)
        cursor: str | None = None
        fields = (
            "classification_id",
            "attribute_extraction_id",
            "attribute_normalization_id",
            "attribute_conflict_detection_id",
            "attribute_validation_id",
            "attribute_completeness_id",
            "review_id",
            "reviewed_attribute_materialization_id",
            "projection_id",
            "enrichment_id",
        )
        while True:
            page = self._jobs.list_by_product(workflow.product_id, limit=100, cursor=cursor)
            for job in page.items:
                if self._reusable(job, job_type) and all(
                    getattr(job, field) == getattr(expected, field) for field in fields
                ):
                    return job
            cursor = page.next_cursor
            if cursor is None:
                return None

    @staticmethod
    def _reusable(job: ProcessingJob, job_type: ProcessingJobType) -> bool:
        return (
            job.job_type is job_type
            and job.status is ProcessingJobStatus.COMPLETED
            and job.result_reference is not None
        )

    @staticmethod
    def _completed_reference(job: ProcessingJob) -> str:
        if job.result_reference is None:
            raise ValueError("completed job result reference is missing")
        return job.result_reference
