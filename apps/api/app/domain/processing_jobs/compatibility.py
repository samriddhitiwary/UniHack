"""Source-type compatibility policy for processing-job creation."""

from app.domain.processing_jobs.enums import ProcessingJobType
from app.domain.product_sources import ProductSourceType

_SUPPORTED_JOB_TYPES: dict[ProductSourceType, frozenset[ProcessingJobType]] = {
    ProductSourceType.TEXT: frozenset({ProcessingJobType.SOURCE_PROCESSING}),
    ProductSourceType.PDF: frozenset(
        {
            ProcessingJobType.SOURCE_PROCESSING,
            ProcessingJobType.PDF_TEXT_EXTRACTION,
            ProcessingJobType.PDF_TABLE_EXTRACTION,
        }
    ),
    ProductSourceType.IMAGE: frozenset(
        {ProcessingJobType.SOURCE_PROCESSING, ProcessingJobType.IMAGE_ANALYSIS}
    ),
    ProductSourceType.CSV: frozenset(
        {ProcessingJobType.SOURCE_PROCESSING, ProcessingJobType.CSV_PROCESSING}
    ),
}


def is_processing_job_type_supported(
    source_type: ProductSourceType,
    job_type: ProcessingJobType,
) -> bool:
    """Return whether a source may create the requested metadata-only job type."""
    return job_type in _SUPPORTED_JOB_TYPES[source_type]
