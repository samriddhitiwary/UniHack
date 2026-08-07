"""Deterministic PDF extraction fixtures and tiny generated PDFs."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.pdf_extraction import PdfExtractionPage, PdfTextExtractionResult
from tests.fixtures.processing_jobs import JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

EXTRACTION_ID = UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")
EXTRACTION_CREATED_AT = datetime(2026, 8, 7, 7, 0, tzinfo=UTC)


def make_pdf_extraction_result(
    *,
    extraction_id: UUID = EXTRACTION_ID,
    pages: tuple[PdfExtractionPage, ...] | None = None,
) -> PdfTextExtractionResult:
    evidence = pages or (
        PdfExtractionPage.create(1, "Pump model PX-400\nMaximum pressure 16 bar"),
        PdfExtractionPage.create(2, "Materials and operating limits"),
    )
    created = PdfTextExtractionResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        parser="pypdf",
        parser_version="6.15.0",
        pages=evidence,
        now=EXTRACTION_CREATED_AT,
    )
    return PdfTextExtractionResult(
        extraction_id=extraction_id,
        job_id=created.job_id,
        product_id=created.product_id,
        source_id=created.source_id,
        parser=created.parser,
        parser_version=created.parser_version,
        page_count=created.page_count,
        pages_with_text=created.pages_with_text,
        total_character_count=created.total_character_count,
        quality_status=created.quality_status,
        pages=created.pages,
        warning_codes=created.warning_codes,
        created_at=created.created_at,
    )


def make_pdf_bytes(page_lines: list[list[str]]) -> bytes:
    """Generate a tiny text/blank PDF without copyrighted fixture content."""
    objects: list[bytes] = []
    page_references = " ".join(f"{4 + index * 2} 0 R" for index in range(len(page_lines)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(
        f"<< /Type /Pages /Kids [{page_references}] /Count {len(page_lines)} >>".encode()
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for index, lines in enumerate(page_lines):
        content_number = 5 + index * 2
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>"
            ).encode()
        )
        commands = ["BT /F1 12 Tf 72 720 Td"]
        for line_index, line in enumerate(lines):
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            if line_index:
                commands.append("0 -16 Td")
            commands.append(f"({escaped}) Tj")
        commands.append("ET")
        stream = "\n".join(commands).encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)
