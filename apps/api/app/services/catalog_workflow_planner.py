"""Pure fixed stage and source child-job planning for CATALOG_INTELLIGENCE."""

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from app.domain.catalog_workflow import CatalogWorkflowSourceSnapshot
from app.domain.processing_jobs import ProcessingJobType
from app.domain.product_sources import ProductSourceType


@dataclass(frozen=True, slots=True, kw_only=True)
class CatalogWorkflowSourceJobPlan:
    source_id: UUID
    job_types: tuple[ProcessingJobType, ...]


class CatalogWorkflowPlanner:
    _JOBS: ClassVar[dict[ProductSourceType, tuple[ProcessingJobType, ...]]] = {
        ProductSourceType.TEXT: (),
        ProductSourceType.PDF: (
            ProcessingJobType.PDF_TEXT_EXTRACTION,
            ProcessingJobType.PDF_TABLE_EXTRACTION,
        ),
        ProductSourceType.CSV: (ProcessingJobType.CSV_PROCESSING,),
        ProductSourceType.IMAGE: (
            ProcessingJobType.IMAGE_ANALYSIS,
            ProcessingJobType.IMAGE_OCR,
        ),
    }

    def plan_sources(
        self, sources: tuple[CatalogWorkflowSourceSnapshot, ...]
    ) -> tuple[CatalogWorkflowSourceJobPlan, ...]:
        plans = tuple(
            CatalogWorkflowSourceJobPlan(
                source_id=source.source_id,
                job_types=self._JOBS[source.source_type],
            )
            for source in sources
        )
        if sum(len(plan.job_types) for plan in plans) > 200:
            raise ValueError("workflow child-job limit exceeded")
        return plans
