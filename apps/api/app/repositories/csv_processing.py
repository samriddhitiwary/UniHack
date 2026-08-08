"""CSV processing-result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.csv_processing import CsvProcessingResult


class CsvProcessingResultRepository(Protocol):
    def create(self, result: CsvProcessingResult) -> CsvProcessingResult: ...
    def get_by_id(self, processing_id: UUID) -> CsvProcessingResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> CsvProcessingResult | None: ...
