"""Product-level structured attribute extraction job orchestration."""

import logging
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import (
    CategoryAttributeSchemaRepositoryError,
    InvalidStructuredAttributeExtractionJobError,
    ProcessingJobRepositoryError,
    ProductClassificationRepositoryError,
    ProductRepositoryError,
    StructuredAttributeExtractionError,
    StructuredAttributeExtractionPrerequisiteError,
    StructuredAttributeExtractionRepositoryError,
    StructuredAttributeExtractionResultStorageError,
)
from app.domain.attribute_extraction import StructuredAttributeExtractionResult
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.domain.product_classification import ProductClassificationStatus
from app.repositories.category_schemas import CategoryAttributeSchemaRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.repositories.product_classification import ProductClassificationResultRepository
from app.repositories.products import ProductRepository
from app.repositories.structured_attribute_extraction import (
    StructuredAttributeExtractionResultRepository,
)
from app.services.structured_attribute_evidence import StructuredAttributeEvidenceAggregator
from app.services.structured_attribute_extraction_engine import StructuredAttributeExtractionEngine

logger = logging.getLogger(__name__)


class StructuredAttributeExtractionService:
    def __init__(
        self,
        *,
        job_repository: ProcessingJobRepository,
        product_repository: ProductRepository,
        classification_repository: ProductClassificationResultRepository,
        schema_repository: CategoryAttributeSchemaRepository,
        result_repository: StructuredAttributeExtractionResultRepository,
        evidence_aggregator: StructuredAttributeEvidenceAggregator,
        engine: StructuredAttributeExtractionEngine,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._jobs, self._products = job_repository, product_repository
        self._classifications, self._schemas = classification_repository, schema_repository
        self._results, self._evidence, self._engine = result_repository, evidence_aggregator, engine
        self._clock = clock or (lambda: datetime.now(UTC))

    def extract_for_job(self, *, job_id: UUID) -> StructuredAttributeExtractionResult:
        job = self._jobs.get_by_id(job_id)
        if (
            job is None
            or job.job_type is not ProcessingJobType.ATTRIBUTE_EXTRACTION
            or job.status is not ProcessingJobStatus.PENDING
            or job.source_id is not None
            or job.classification_id is None
        ):
            raise InvalidStructuredAttributeExtractionJobError()
        try:
            product = self._products.get_by_id(job.product_id)
            classification = self._classifications.get_by_id(job.classification_id)
            if (
                product is None
                or classification is None
                or classification.product_id != job.product_id
                or classification.status is not ProductClassificationStatus.CLASSIFIED
            ):
                raise StructuredAttributeExtractionPrerequisiteError()
            schema = self._schemas.get_active_by_category(classification.category)
            if schema is None or schema.category is not classification.category:
                raise StructuredAttributeExtractionPrerequisiteError()
            if self._results.get_by_job_id(job.job_id) is not None:
                raise InvalidStructuredAttributeExtractionJobError()
        except StructuredAttributeExtractionError:
            raise
        except (
            ProductRepositoryError,
            ProductClassificationRepositoryError,
            CategoryAttributeSchemaRepositoryError,
            StructuredAttributeExtractionRepositoryError,
        ) as exc:
            raise StructuredAttributeExtractionPrerequisiteError() from exc
        running = self._jobs.update(
            transition_processing_job(job, ProcessingJobStatus.RUNNING, now=self._clock()),
            expected_version=job.version,
        )
        try:
            evidence, aggregation_warnings = self._evidence.collect(job.product_id)
            candidates, engine_warnings, duplicate_count = self._engine.extract(
                schema=schema, evidence=evidence, now=self._clock()
            )
            warnings = tuple(dict.fromkeys((*aggregation_warnings, *engine_warnings)))
            result = StructuredAttributeExtractionResult.create(
                job_id=job.job_id,
                product_id=job.product_id,
                classification_id=classification.classification_id,
                category=classification.category,
                schema_version=schema.version,
                schema_fingerprint=schema.schema_fingerprint,
                evidence_item_count=len(evidence),
                candidates=candidates,
                duplicate_count=duplicate_count,
                warning_codes=warnings,
                now=self._clock(),
            )
            stored = self._results.create(result)
        except StructuredAttributeExtractionError as exc:
            self._fail(running, exc)
            raise
        except StructuredAttributeExtractionRepositoryError as exc:
            error = StructuredAttributeExtractionResultStorageError()
            self._fail(running, error)
            raise error from exc
        except Exception as exc:
            unexpected_error = StructuredAttributeExtractionError()
            self._fail(running, unexpected_error)
            raise unexpected_error from exc
        completed = replace(
            running,
            result_reference=f"structured-attribute-extraction-results/{stored.extraction_id}",
        )
        completed = transition_processing_job(
            completed, ProcessingJobStatus.COMPLETED, now=self._clock()
        )
        try:
            self._jobs.update(completed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.error(
                "event=attribute_extraction.completion_consistency_risk job_id=%s "
                "product_id=%s extraction_id=%s",
                job.job_id,
                job.product_id,
                stored.extraction_id,
            )
            raise
        logger.info(
            "event=attribute_extraction.%s job_id=%s product_id=%s classification_id=%s "
            "category=%s schema_version=%s evidence_count=%s candidate_count=%s duplicate_count=%s",
            stored.status.value.lower(),
            job.job_id,
            job.product_id,
            job.classification_id,
            stored.category.value,
            stored.schema_version,
            stored.evidence_item_count,
            stored.candidate_count,
            stored.duplicate_count,
        )
        return stored

    def _fail(self, running: ProcessingJob, error: StructuredAttributeExtractionError) -> None:
        failed = replace(running, error_code=error.code, error_message=error.safe_message)
        failed = transition_processing_job(failed, ProcessingJobStatus.FAILED, now=self._clock())
        try:
            self._jobs.update(failed, expected_version=running.version)
        except ProcessingJobRepositoryError:
            logger.exception(
                "event=attribute_extraction.completion_consistency_risk job_id=%s", running.job_id
            )
