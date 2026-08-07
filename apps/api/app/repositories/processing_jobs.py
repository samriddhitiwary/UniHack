"""Processing-job repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.processing_jobs import ProcessingJob, ProcessingJobPage


class ProcessingJobRepository(Protocol):
    def create(self, job: ProcessingJob) -> ProcessingJob: ...

    def get_by_id(self, job_id: UUID) -> ProcessingJob | None: ...

    def list_by_product(
        self, product_id: UUID, *, limit: int = 25, cursor: str | None = None
    ) -> ProcessingJobPage: ...

    def list_by_source(
        self,
        product_id: UUID,
        source_id: UUID,
        *,
        limit: int = 25,
        cursor: str | None = None,
    ) -> ProcessingJobPage: ...

    def update(self, job: ProcessingJob, expected_version: int) -> ProcessingJob: ...
