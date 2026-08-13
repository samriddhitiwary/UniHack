"""Configuration contract tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_blank_aws_endpoint_selects_normal_aws_behavior() -> None:
    settings = Settings(dynamodb_endpoint_url="")
    assert settings.dynamodb_endpoint_url is None


def test_table_names_are_derived_from_prefix() -> None:
    settings = Settings(dynamodb_table_prefix="catalogiq-test")
    assert settings.table_name("jobs") == "catalogiq-test-jobs"


def test_invalid_table_resource_is_rejected() -> None:
    settings = Settings()
    with pytest.raises(ValueError, match="resource"):
        settings.table_name("bad resource")


def test_comma_separated_cors_origins_are_supported() -> None:
    settings = Settings(cors_allowed_origins="https://one.example,https://two.example")
    assert settings.cors_allowed_origins == ["https://one.example", "https://two.example"]


def test_relative_local_storage_root_resolves_from_api_project() -> None:
    settings = Settings(local_storage_root="../../storage")
    expected = Path(__file__).resolve().parents[4] / "storage"
    assert settings.local_storage_path() == expected.resolve()


def test_blank_local_storage_root_is_rejected() -> None:
    with pytest.raises(ValidationError, match="local_storage_root must not be blank"):
        Settings(local_storage_root="")


@pytest.mark.parametrize(
    "field", ["max_pdf_upload_bytes", "max_image_upload_bytes", "max_csv_upload_bytes"]
)
def test_upload_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "pdf_extraction_max_pages",
        "pdf_extraction_max_total_characters",
        "pdf_extraction_max_page_characters",
    ],
)
def test_pdf_extraction_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "pdf_table_extraction_max_pages",
        "pdf_table_extraction_max_tables",
        "pdf_table_extraction_max_rows_per_table",
        "pdf_table_extraction_max_columns_per_table",
        "pdf_table_extraction_max_cells",
        "pdf_table_extraction_max_cell_characters",
    ],
)
def test_pdf_table_extraction_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "csv_processing_max_file_bytes",
        "csv_processing_max_rows",
        "csv_processing_max_columns",
        "csv_processing_max_total_cells",
        "csv_processing_max_cell_characters",
        "csv_processing_sample_bytes",
    ],
)
def test_csv_processing_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "image_analysis_max_file_bytes",
        "image_analysis_max_width",
        "image_analysis_max_height",
        "image_analysis_max_pixels",
        "image_analysis_max_regions",
    ],
)
def test_image_analysis_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize(
    "field",
    [
        "image_ocr_max_regions",
        "image_ocr_max_blocks",
        "image_ocr_max_total_characters",
        "image_ocr_max_block_characters",
    ],
)
def test_image_ocr_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: 0})


@pytest.mark.parametrize("value", [-1, 10_001])
def test_image_ocr_confidence_threshold_is_bounded(value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(image_ocr_min_confidence_bp=value)
