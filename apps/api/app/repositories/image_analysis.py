"""Image-analysis result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.image_analysis import ImageAnalysisResult


class ImageAnalysisResultRepository(Protocol):
    def create(self, result: ImageAnalysisResult) -> ImageAnalysisResult: ...
    def get_by_id(self, analysis_id: UUID) -> ImageAnalysisResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> ImageAnalysisResult | None: ...
