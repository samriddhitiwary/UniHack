"""Bounded heterogeneous classification-evidence aggregation tests."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import ProductClassificationEvidenceLimitExceededError
from app.domain.processing_jobs import ProcessingJobStatus, ProcessingJobType
from app.domain.product_classification import ClassificationEvidenceType
from app.domain.product_sources import ProductSourceType
from app.services.product_classification_evidence import (
    ProductClassificationEvidenceAggregator,
)


class Sources:
    def __init__(self, items):
        self.items = tuple(items)

    def list_by_product(self, product_id, *, limit=25, cursor=None):
        return SimpleNamespace(items=self.items, next_cursor=None)


class Jobs:
    def __init__(self, jobs):
        self.jobs = jobs

    def list_by_source(self, product_id, source_id, *, limit=25, cursor=None):
        return SimpleNamespace(items=tuple(self.jobs.get(source_id, ())), next_cursor=None)


class Results:
    def __init__(self, values):
        self.values = values

    def get_by_job_id(self, job_id):
        return self.values.get(job_id)


def source(kind, product_id):
    return SimpleNamespace(
        source_id=uuid4(),
        product_id=product_id,
        source_type=kind,
        text_content="centrifugal pump" if kind is ProductSourceType.TEXT else None,
    )


def job(kind):
    return SimpleNamespace(
        job_id=uuid4(),
        job_type=kind,
        status=ProcessingJobStatus.COMPLETED,
    )


def aggregator(*, max_items=5000, max_total=500000, max_item=5000):
    product_id = uuid4()
    text = source(ProductSourceType.TEXT, product_id)
    pdf = source(ProductSourceType.PDF, product_id)
    csv = source(ProductSourceType.CSV, product_id)
    image = source(ProductSourceType.IMAGE, product_id)
    pdf_text_job = job(ProcessingJobType.PDF_TEXT_EXTRACTION)
    pdf_table_job = job(ProcessingJobType.PDF_TABLE_EXTRACTION)
    csv_job = job(ProcessingJobType.CSV_PROCESSING)
    ocr_job = job(ProcessingJobType.IMAGE_OCR)
    jobs = {
        pdf.source_id: (pdf_text_job, pdf_table_job),
        csv.source_id: (csv_job,),
        image.source_id: (ocr_job,),
    }
    pdf_text = SimpleNamespace(pages=(SimpleNamespace(page_number=2, text="induction motor"),))
    cell = SimpleNamespace(column_index=0, text="flow rate")
    table_row = SimpleNamespace(row_index=0, cells=(cell,))
    table = SimpleNamespace(page_number=1, table_index=1, rows=(table_row,))
    pdf_tables = SimpleNamespace(tables=(table,))
    header = SimpleNamespace(column_index=0, text="rated power")
    csv_cell = SimpleNamespace(column_index=0, text="5.5 kW")
    csv_row = SimpleNamespace(row_number=1, cells=(csv_cell,), extra_cells=())
    csv_result = SimpleNamespace(header=(header,), rows=(csv_row,))
    block = SimpleNamespace(
        text="three phase",
        region_id="region-1",
        block_id="block-000001",
        confidence_bp=7500,
    )
    ocr_result = SimpleNamespace(blocks=(block,))
    instance = ProductClassificationEvidenceAggregator(
        source_repository=Sources((text, pdf, csv, image)),
        job_repository=Jobs(jobs),
        pdf_text_repository=Results({pdf_text_job.job_id: pdf_text}),
        pdf_table_repository=Results({pdf_table_job.job_id: pdf_tables}),
        csv_repository=Results({csv_job.job_id: csv_result}),
        image_ocr_repository=Results({ocr_job.job_id: ocr_result}),
        max_items=max_items,
        max_total_characters=max_total,
        max_item_characters=max_item,
    )
    return instance, product_id


def test_collects_every_supported_evidence_type_with_provenance_and_weights() -> None:
    instance, product_id = aggregator()
    evidence = instance.collect(product_id)
    assert tuple(item.evidence_type for item in evidence) == (
        ClassificationEvidenceType.DIRECT_TEXT,
        ClassificationEvidenceType.PDF_TEXT,
        ClassificationEvidenceType.PDF_TABLE_CELL,
        ClassificationEvidenceType.CSV_HEADER,
        ClassificationEvidenceType.CSV_CELL,
        ClassificationEvidenceType.IMAGE_OCR,
    )
    assert tuple(item.weight for item in evidence) == (100, 100, 110, 110, 90, 75)
    assert "pageNumber=2" in evidence[1].location
    assert "tableIndex=1" in evidence[2].location
    assert "headerName=rated power" in evidence[4].location
    assert "regionId=region-1" in evidence[5].location
    assert len({item.source_id for item in evidence}) == 4


@pytest.mark.parametrize(
    ("max_items", "max_total", "max_item"),
    ((1, 500000, 5000), (5000, 5, 5000), (5000, 500000, 5)),
)
def test_evidence_bounds_fail_without_truncation(max_items, max_total, max_item) -> None:
    instance, product_id = aggregator(max_items=max_items, max_total=max_total, max_item=max_item)
    with pytest.raises(ProductClassificationEvidenceLimitExceededError):
        instance.collect(product_id)
