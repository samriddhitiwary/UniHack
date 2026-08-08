"""Deterministic PDF table-extraction fixtures."""

from datetime import UTC, datetime
from uuid import UUID

from app.domain.pdf_table_extraction import (
    PdfExtractedTable,
    PdfTableCell,
    PdfTableExtractionResult,
    PdfTableRow,
)
from tests.fixtures.processing_jobs import JOB_ID
from tests.fixtures.product_sources import SOURCE_ID
from tests.fixtures.products import PRODUCT_ID

TABLE_EXTRACTION_ID = UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd")
TABLE_EXTRACTION_CREATED_AT = datetime(2026, 8, 7, 8, 0, tzinfo=UTC)


def make_table(
    page_number: int = 1,
    table_index: int = 1,
    values: tuple[tuple[str | None, ...], ...] = (("Model", "Pressure"), ("PX-400", "16 bar")),
) -> PdfExtractedTable:
    width = max(len(row) for row in values)
    rows = tuple(
        PdfTableRow(
            row_index,
            tuple(
                PdfTableCell.create(
                    row_index, column_index, row[column_index] if column_index < len(row) else None
                )
                for column_index in range(width)
            ),
        )
        for row_index, row in enumerate(values)
    )
    return PdfExtractedTable(
        table_index=table_index,
        page_number=page_number,
        row_count=len(rows),
        column_count=width,
        cell_count=len(rows) * width,
        rows=rows,
    )


def make_pdf_table_extraction_result(
    *,
    extraction_id: UUID = TABLE_EXTRACTION_ID,
    page_count: int = 2,
    tables: tuple[PdfExtractedTable, ...] | None = None,
) -> PdfTableExtractionResult:
    result = PdfTableExtractionResult.create(
        job_id=JOB_ID,
        product_id=PRODUCT_ID,
        source_id=SOURCE_ID,
        parser="pdfplumber",
        parser_version="0.11.10",
        page_count=page_count,
        tables=tables or (make_table(), make_table(2, 1, (("Part", "Material"), ("Seal", "PTFE")))),
        now=TABLE_EXTRACTION_CREATED_AT,
    )
    return PdfTableExtractionResult(
        extraction_id=extraction_id,
        job_id=result.job_id,
        product_id=result.product_id,
        source_id=result.source_id,
        parser=result.parser,
        parser_version=result.parser_version,
        page_count=result.page_count,
        pages_with_tables=result.pages_with_tables,
        table_count=result.table_count,
        total_row_count=result.total_row_count,
        total_cell_count=result.total_cell_count,
        quality_status=result.quality_status,
        tables=result.tables,
        warning_codes=result.warning_codes,
        created_at=result.created_at,
    )


def make_table_pdf_bytes(pages: list[list[list[list[str]]]]) -> bytes:
    """Generate a tiny line-grid PDF: pages -> tables -> rows -> cells."""
    objects: list[bytes] = []
    page_refs = " ".join(f"{4 + index * 2} 0 R" for index in range(len(pages)))
    objects.extend(
        [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{page_refs}] /Count {len(pages)} >>".encode(),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
    )
    for page_index, page_tables in enumerate(pages):
        content_number = 5 + page_index * 2
        objects.append(
            (
                "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_number} 0 R >>"
            ).encode()
        )
        commands = ["0.8 w"]
        top = 720
        for table in page_tables:
            rows = len(table)
            columns = max(len(row) for row in table)
            cell_width, cell_height = 110, 28
            left, bottom = 60, top - rows * cell_height
            commands.append(f"{left} {bottom} {columns * cell_width} {rows * cell_height} re S")
            for column in range(1, columns):
                x = left + column * cell_width
                commands.append(f"{x} {bottom} m {x} {top} l S")
            for row in range(1, rows):
                y = top - row * cell_height
                commands.append(f"{left} {y} m {left + columns * cell_width} {y} l S")
            for row_index, row in enumerate(table):
                for column_index, value in enumerate(row):
                    escaped = value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                    x = left + column_index * cell_width + 5
                    y = top - (row_index + 1) * cell_height + 9
                    commands.append(f"BT /F1 10 Tf {x} {y} Td ({escaped}) Tj ET")
            top = bottom - 48
        stream = "\n".join(commands).encode()
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)
