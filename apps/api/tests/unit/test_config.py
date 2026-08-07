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
