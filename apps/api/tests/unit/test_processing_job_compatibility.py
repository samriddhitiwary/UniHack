"""Processing-job/source compatibility matrix tests."""

import pytest

from app.domain.processing_jobs import ProcessingJobType, is_processing_job_type_supported
from app.domain.product_sources import ProductSourceType

SUPPORTED = {
    ProductSourceType.TEXT: {ProcessingJobType.SOURCE_PROCESSING},
    ProductSourceType.PDF: {
        ProcessingJobType.SOURCE_PROCESSING,
        ProcessingJobType.PDF_TEXT_EXTRACTION,
        ProcessingJobType.PDF_TABLE_EXTRACTION,
    },
    ProductSourceType.IMAGE: {
        ProcessingJobType.SOURCE_PROCESSING,
        ProcessingJobType.IMAGE_ANALYSIS,
    },
    ProductSourceType.CSV: {
        ProcessingJobType.SOURCE_PROCESSING,
        ProcessingJobType.CSV_PROCESSING,
    },
}


@pytest.mark.parametrize(
    ("source_type", "job_type"),
    [
        (source_type, job_type)
        for source_type in ProductSourceType
        for job_type in ProcessingJobType
    ],
)
def test_exact_source_job_compatibility_matrix(
    source_type: ProductSourceType,
    job_type: ProcessingJobType,
) -> None:
    assert is_processing_job_type_supported(source_type, job_type) is (
        job_type in SUPPORTED[source_type]
    )
