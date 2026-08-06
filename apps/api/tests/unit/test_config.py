"""Configuration contract tests."""

import pytest

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
