"""Processing-job domain enumerations."""

from enum import StrEnum


class ProcessingJobType(StrEnum):
    SOURCE_PROCESSING = "SOURCE_PROCESSING"
    PDF_TEXT_EXTRACTION = "PDF_TEXT_EXTRACTION"
    PDF_TABLE_EXTRACTION = "PDF_TABLE_EXTRACTION"
    IMAGE_ANALYSIS = "IMAGE_ANALYSIS"
    CSV_PROCESSING = "CSV_PROCESSING"


class ProcessingJobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
