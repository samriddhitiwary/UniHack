"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated configuration shared by local development and AWS."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "CatalogIQ API"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)

    aws_region: str = "ap-south-1"
    dynamodb_endpoint_url: str | None = "http://localhost:8001"
    dynamodb_table_prefix: str = "catalogiq-dev"

    storage_backend: Literal["local", "s3"] = "local"
    local_storage_root: Path = Path("../../storage")
    s3_bucket_name: str | None = None

    cors_allowed_origins: list[str] = ["http://localhost:5173"]
    max_pdf_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_image_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_csv_upload_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    pdf_extraction_max_pages: int = Field(default=300, gt=0)
    pdf_extraction_max_total_characters: int = Field(default=2_000_000, gt=0)
    pdf_extraction_max_page_characters: int = Field(default=100_000, gt=0)
    pdf_table_extraction_max_pages: int = Field(default=300, gt=0)
    pdf_table_extraction_max_tables: int = Field(default=500, gt=0)
    pdf_table_extraction_max_rows_per_table: int = Field(default=5_000, gt=0)
    pdf_table_extraction_max_columns_per_table: int = Field(default=200, gt=0)
    pdf_table_extraction_max_cells: int = Field(default=500_000, gt=0)
    pdf_table_extraction_max_cell_characters: int = Field(default=20_000, gt=0)
    csv_processing_max_file_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    csv_processing_max_rows: int = Field(default=100_000, gt=0)
    csv_processing_max_columns: int = Field(default=500, gt=0)
    csv_processing_max_total_cells: int = Field(default=1_000_000, gt=0)
    csv_processing_max_cell_characters: int = Field(default=50_000, gt=0)
    csv_processing_sample_bytes: int = Field(default=65_536, gt=0)
    image_analysis_max_file_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    image_analysis_max_width: int = Field(default=12_000, gt=0)
    image_analysis_max_height: int = Field(default=12_000, gt=0)
    image_analysis_max_pixels: int = Field(default=80_000_000, gt=0)
    image_analysis_max_regions: int = Field(default=16, gt=0)
    image_ocr_max_regions: int = Field(default=6, gt=0)
    image_ocr_max_blocks: int = Field(default=5_000, gt=0)
    image_ocr_max_total_characters: int = Field(default=500_000, gt=0)
    image_ocr_max_block_characters: int = Field(default=10_000, gt=0)
    image_ocr_min_confidence_bp: int = Field(default=4_000, ge=0, le=10_000)
    product_classification_max_evidence_items: int = Field(default=5_000, gt=0)
    product_classification_max_total_characters: int = Field(default=500_000, gt=0)
    product_classification_max_item_characters: int = Field(default=5_000, gt=0)
    product_classification_max_matches: int = Field(default=1_000, gt=0)
    log_level: str = "INFO"

    @field_validator("dynamodb_endpoint_url", "s3_bucket_name", mode="before")
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        """Treat blank optional environment values as absent."""
        return None if value == "" else value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        """Accept the comma-separated form used by environment files."""
        if isinstance(value, str) and not value.lstrip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("local_storage_root", mode="before")
    @classmethod
    def local_storage_root_is_not_blank(cls, value: object) -> object:
        """Reject a blank path, which would otherwise select the process directory."""
        if isinstance(value, str) and not value.strip():
            raise ValueError("local_storage_root must not be blank")
        return value

    def table_name(self, resource: str) -> str:
        """Derive a future table name without embedding names in repositories."""
        normalized = resource.strip().lower()
        if not normalized or not normalized.replace("-", "").isalnum():
            raise ValueError("resource must contain only letters, numbers, or hyphens")
        return f"{self.dynamodb_table_prefix}-{normalized}"

    def local_storage_path(self) -> Path:
        """Resolve relative storage roots from the API project directory."""
        root = self.local_storage_root.expanduser()
        if not root.is_absolute():
            root = Path(__file__).resolve().parents[2] / root
        return root.resolve()


@lru_cache
def get_settings() -> Settings:
    """Load and cache validated application settings."""
    return Settings()
