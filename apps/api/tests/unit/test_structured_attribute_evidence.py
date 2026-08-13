from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import StructuredAttributeExtractionLimitExceededError
from app.domain.attribute_extraction import AttributeExtractionEvidenceType
from app.domain.processing_jobs import ProcessingJobStatus, ProcessingJobType
from app.domain.product_sources import ProductSourceType
from app.services.structured_attribute_evidence import StructuredAttributeEvidenceAggregator


class Pages:
    def __init__(self, items):
        self.items = tuple(items)

    def list_by_product(self, product_id, *, limit=25, cursor=None):
        return SimpleNamespace(items=self.items, next_cursor=None)


class Jobs:
    def __init__(self, values):
        self.values = values

    def list_by_source(self, product_id, source_id, *, limit=25, cursor=None):
        return SimpleNamespace(items=tuple(self.values.get(source_id, ())), next_cursor=None)


class Results:
    def __init__(self, values):
        self.values = values

    def get_by_job_id(self, job_id):
        return self.values.get(job_id)


def make_source(kind, product_id, text=None):
    return SimpleNamespace(
        source_id=uuid4(), product_id=product_id, source_type=kind, text_content=text
    )


def make_job(kind):
    return SimpleNamespace(job_id=uuid4(), job_type=kind, status=ProcessingJobStatus.COMPLETED)


def fixture(*, csv_rows=1, max_items=10_000):
    product_id = uuid4()
    text = make_source(ProductSourceType.TEXT, product_id, "Voltage: 415 V")
    pdf = make_source(ProductSourceType.PDF, product_id)
    csv = make_source(ProductSourceType.CSV, product_id)
    image = make_source(ProductSourceType.IMAGE, product_id)
    text_job, table_job = (
        make_job(ProcessingJobType.PDF_TEXT_EXTRACTION),
        make_job(ProcessingJobType.PDF_TABLE_EXTRACTION),
    )
    csv_job, ocr_job = (
        make_job(ProcessingJobType.CSV_PROCESSING),
        make_job(ProcessingJobType.IMAGE_OCR),
    )
    jobs = {
        pdf.source_id: (text_job, table_job),
        csv.source_id: (csv_job,),
        image.source_id: (ocr_job,),
    }
    pdf_text = SimpleNamespace(pages=(SimpleNamespace(page_number=1, text="Frequency: 50 Hz"),))
    table = SimpleNamespace(
        page_number=1,
        table_index=1,
        rows=(
            SimpleNamespace(
                row_index=0,
                cells=(
                    SimpleNamespace(text="Speed", column_index=0),
                    SimpleNamespace(text="1450 rpm", column_index=1),
                ),
            ),
            SimpleNamespace(
                row_index=1, cells=(SimpleNamespace(text="unstructured", column_index=0),)
            ),
        ),
    )
    csv_result = SimpleNamespace(
        row_count=csv_rows,
        header=(SimpleNamespace(text="Rated Power", column_index=0),),
        rows=tuple(
            SimpleNamespace(cells=(SimpleNamespace(text="5.5 kW", column_index=0),))
            for _ in range(csv_rows)
        ),
    )
    ocr = SimpleNamespace(
        blocks=(
            SimpleNamespace(
                text="Current: 10.8 A",
                region_id="region-1",
                block_id="block-000001",
                confidence_bp=7_500,
            ),
        )
    )
    return StructuredAttributeEvidenceAggregator(
        source_repository=Pages((text, pdf, csv, image)),
        job_repository=Jobs(jobs),
        pdf_text_repository=Results({text_job.job_id: pdf_text}),
        pdf_table_repository=Results({table_job.job_id: SimpleNamespace(tables=(table,))}),
        csv_repository=Results({csv_job.job_id: csv_result}),
        image_ocr_repository=Results({ocr_job.job_id: ocr}),
        max_items=max_items,
    ), product_id


def test_collects_all_supported_persisted_evidence_with_provenance() -> None:
    aggregator, product_id = fixture()
    items, warnings = aggregator.collect(product_id)
    assert tuple(item.evidence_type for item in items) == (
        AttributeExtractionEvidenceType.DIRECT_TEXT,
        AttributeExtractionEvidenceType.PDF_TEXT,
        AttributeExtractionEvidenceType.PDF_TABLE_ROW,
        AttributeExtractionEvidenceType.PDF_TABLE_CELL,
        AttributeExtractionEvidenceType.CSV_CELL,
        AttributeExtractionEvidenceType.IMAGE_OCR,
    )
    assert items[2].label_hint == "Speed" and items[2].value_hint == "1450 rpm"
    assert items[4].label_hint == "Rated Power" and items[4].source_quality_bp == 9_500
    assert items[5].source_quality_bp == 7_500 and warnings == ()


def test_multirow_csv_is_skipped_with_warning() -> None:
    aggregator, product_id = fixture(csv_rows=2)
    items, warnings = aggregator.collect(product_id)
    assert not any(item.evidence_type is AttributeExtractionEvidenceType.CSV_CELL for item in items)
    assert warnings == ("MULTI_ROW_CSV_SKIPPED",)


def test_evidence_limit_fails_without_truncation() -> None:
    aggregator, product_id = fixture(max_items=1)
    with pytest.raises(StructuredAttributeExtractionLimitExceededError):
        aggregator.collect(product_id)
