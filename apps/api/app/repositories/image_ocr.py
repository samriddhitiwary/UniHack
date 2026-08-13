"""Image OCR result repository contract."""

from typing import Protocol
from uuid import UUID

from app.domain.image_ocr import ImageOcrResult


class ImageOcrResultRepository(Protocol):
    def create(self, result: ImageOcrResult) -> ImageOcrResult: ...
    def get_by_id(self, ocr_id: UUID) -> ImageOcrResult | None: ...
    def get_by_job_id(self, job_id: UUID) -> ImageOcrResult | None: ...
