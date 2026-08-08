"""Controlled application exceptions."""

from uuid import UUID


class ProductRepositoryError(Exception):
    """Base error for product persistence failures."""


class ProductAlreadyExistsError(ProductRepositoryError):
    """Raised when a create would overwrite an existing product."""

    def __init__(self, product_id: UUID | str) -> None:
        self.product_id = str(product_id)
        super().__init__("product already exists")


class ProductNotFoundError(ProductRepositoryError):
    """Raised when an explicit product mutation targets no stored product."""

    def __init__(self, product_id: UUID | str) -> None:
        self.product_id = str(product_id)
        super().__init__("product does not exist")


class ProductVersionConflictError(ProductRepositoryError):
    """Raised when optimistic concurrency rejects a stale product mutation."""


class InvalidProductCursorError(ProductRepositoryError):
    """Raised when an opaque product pagination cursor is invalid."""


class ProductSerializationError(ProductRepositoryError):
    """Raised when product data cannot safely cross the DynamoDB boundary."""


class ProductSourceRepositoryError(Exception):
    """Base error for product-source persistence failures."""


class ProductSourceAlreadyExistsError(ProductSourceRepositoryError):
    """Raised when a source create would overwrite an existing composite key."""


class ProductSourceNotFoundError(ProductSourceRepositoryError):
    """Raised when an explicit source mutation targets no stored source."""

    def __init__(
        self,
        product_id: UUID | str,
        source_id: UUID | str | None = None,
    ) -> None:
        self.product_id = str(product_id)
        self.source_id = str(source_id) if source_id is not None else None
        super().__init__("product source does not exist")


class ProductSourceVersionConflictError(ProductSourceRepositoryError):
    """Raised when optimistic concurrency rejects a stale source mutation."""


class InvalidProductSourceStatusTransitionError(Exception):
    """Raised when a source status cannot move directly to the requested status."""

    def __init__(
        self,
        source_id: UUID | str,
        current_status: str,
        requested_status: str,
    ) -> None:
        self.source_id = str(source_id)
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__("product source status transition is not allowed")


class ProductSourceStorageConsistencyError(Exception):
    """Raised when file-backed source metadata cannot identify its stored object."""

    def __init__(
        self,
        product_id: UUID | str,
        source_id: UUID | str,
        source_type: str,
    ) -> None:
        self.product_id = str(product_id)
        self.source_id = str(source_id)
        self.source_type = source_type
        super().__init__("product source storage metadata is inconsistent")


class ProcessingJobRepositoryError(Exception):
    """Base error for processing-job persistence failures."""


class ProcessingJobAlreadyExistsError(ProcessingJobRepositoryError):
    """Raised when a create would overwrite an existing job."""


class ProcessingJobNotFoundError(ProcessingJobRepositoryError):
    """Raised when a conditional job mutation finds no record."""

    def __init__(self, job_id: UUID | str) -> None:
        self.job_id = str(job_id)
        super().__init__("processing job does not exist")


class ProcessingJobVersionConflictError(ProcessingJobRepositoryError):
    """Raised when optimistic concurrency rejects a stale job mutation."""


class InvalidProcessingJobCursorError(ProcessingJobRepositoryError):
    """Raised when an opaque processing-job cursor is invalid."""


class ProcessingJobSerializationError(ProcessingJobRepositoryError):
    """Raised when job data cannot safely cross the DynamoDB boundary."""


class InvalidProcessingJobStatusTransitionError(Exception):
    """Raised when a job status transition is not approved."""

    def __init__(self, job_id: UUID | str, current_status: str, requested_status: str) -> None:
        self.job_id = str(job_id)
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__("processing-job status transition is not allowed")


class ProcessingJobTypeNotSupportedForSourceError(Exception):
    """Raised when a source cannot use the requested processing-job category."""

    def __init__(self, source_type: str, job_type: str) -> None:
        self.source_type = source_type
        self.job_type = job_type
        super().__init__("processing-job type is not supported for source type")


class PdfTextExtractionError(Exception):
    """Base controlled PDF extraction failure with safe job metadata."""

    code = "PDF_EXTRACTION_FAILED"
    safe_message = "PDF text extraction failed."


class InvalidPdfExtractionJobError(PdfTextExtractionError):
    """Raised when a job cannot begin PDF text extraction."""

    code = "PDF_EXTRACTION_JOB_INVALID"
    safe_message = "The processing job is not eligible for PDF text extraction."


class InvalidPdfSourceError(PdfTextExtractionError):
    """Raised when a job does not reference a usable stored PDF source."""

    code = "PDF_SOURCE_INVALID"
    safe_message = "The processing job does not reference a valid stored PDF source."


class PdfParseError(PdfTextExtractionError):
    """Raised when pypdf cannot structurally read or extract a PDF."""

    code = "PDF_PARSE_FAILED"
    safe_message = "The PDF could not be read for embedded text extraction."


class PdfExtractionPageLimitExceededError(PdfTextExtractionError):
    """Raised when a PDF contains more pages than configured."""

    code = "PDF_EXTRACTION_PAGE_LIMIT_EXCEEDED"
    safe_message = "The PDF exceeds the configured extraction page limit."


class PdfExtractionTextLimitExceededError(PdfTextExtractionError):
    """Raised when one page or the whole result exceeds configured text limits."""

    code = "PDF_EXTRACTION_TEXT_LIMIT_EXCEEDED"
    safe_message = "The PDF exceeds the configured extracted-text limit."


class PdfExtractionObjectNotFoundError(PdfTextExtractionError):
    """Raised when the source's stored PDF object is absent."""

    code = "PDF_OBJECT_NOT_FOUND"
    safe_message = "The stored PDF object could not be found."


class PdfExtractionObjectStorageError(PdfTextExtractionError):
    """Raised when object storage cannot provide the source PDF."""

    code = "PDF_OBJECT_STORAGE_FAILED"
    safe_message = "The stored PDF object is temporarily unavailable."


class PdfExtractionRepositoryError(Exception):
    """Base error for extraction-result persistence failures."""


class PdfExtractionResultAlreadyExistsError(PdfExtractionRepositoryError):
    """Raised when conditional result creation finds the identity already stored."""


class PdfExtractionSerializationError(PdfExtractionRepositoryError):
    """Raised when extraction data cannot safely cross the DynamoDB boundary."""


class PdfExtractionResultStorageError(PdfTextExtractionError):
    """Safe lifecycle metadata for extraction-result repository failures."""

    code = "PDF_EXTRACTION_STORAGE_FAILED"
    safe_message = "The PDF extraction result could not be stored."


class PdfTableExtractionError(Exception):
    """Base controlled PDF table-extraction failure with safe job metadata."""

    code = "PDF_TABLE_EXTRACTION_FAILED"
    safe_message = "PDF table extraction failed."


class InvalidPdfTableExtractionJobError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_JOB_INVALID"
    safe_message = "The processing job is not eligible for PDF table extraction."


class InvalidPdfTableSourceError(PdfTableExtractionError):
    code = "PDF_TABLE_SOURCE_INVALID"
    safe_message = "The processing job does not reference a valid stored PDF source."


class PdfTableParseError(PdfTableExtractionError):
    code = "PDF_TABLE_PARSE_FAILED"
    safe_message = "The PDF could not be read for table extraction."


class PdfTableExtractionPageLimitExceededError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_PAGE_LIMIT_EXCEEDED"
    safe_message = "The PDF exceeds the configured table-extraction page limit."


class PdfTableExtractionTableLimitExceededError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_TABLE_LIMIT_EXCEEDED"
    safe_message = "The PDF exceeds the configured extracted-table limit."


class PdfTableExtractionRowLimitExceededError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_ROW_LIMIT_EXCEEDED"
    safe_message = "A PDF table exceeds the configured row limit."


class PdfTableExtractionColumnLimitExceededError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_COLUMN_LIMIT_EXCEEDED"
    safe_message = "A PDF table exceeds the configured column limit."


class PdfTableExtractionCellLimitExceededError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_CELL_LIMIT_EXCEEDED"
    safe_message = "The PDF exceeds the configured extracted-cell limit."


class PdfTableExtractionCellTextLimitExceededError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_CELL_TEXT_LIMIT_EXCEEDED"
    safe_message = "A PDF table cell exceeds the configured text limit."


class PdfTableExtractionObjectNotFoundError(PdfTableExtractionError):
    code = "PDF_TABLE_OBJECT_NOT_FOUND"
    safe_message = "The stored PDF object could not be found."


class PdfTableExtractionObjectStorageError(PdfTableExtractionError):
    code = "PDF_TABLE_OBJECT_STORAGE_FAILED"
    safe_message = "The stored PDF object is temporarily unavailable."


class PdfTableExtractionRepositoryError(Exception):
    """Base error for PDF table-result persistence failures."""


class PdfTableExtractionResultAlreadyExistsError(PdfTableExtractionRepositoryError):
    """Raised when conditional creation finds an existing result identity."""


class PdfTableExtractionSerializationError(PdfTableExtractionRepositoryError):
    """Raised when table evidence cannot safely cross the DynamoDB boundary."""


class PdfTableExtractionResultStorageError(PdfTableExtractionError):
    code = "PDF_TABLE_EXTRACTION_STORAGE_FAILED"
    safe_message = "The PDF table-extraction result could not be stored."


class CsvProcessingError(Exception):
    """Base controlled CSV processing failure with safe job metadata."""

    code = "CSV_PROCESSING_FAILED"
    safe_message = "CSV processing failed."


class InvalidCsvProcessingJobError(CsvProcessingError):
    code = "CSV_PROCESSING_JOB_INVALID"
    safe_message = "The processing job is not eligible for CSV processing."


class InvalidCsvSourceError(CsvProcessingError):
    code = "CSV_SOURCE_INVALID"
    safe_message = "The processing job does not reference a valid stored CSV source."


class CsvEncodingUnsupportedError(CsvProcessingError):
    code = "CSV_ENCODING_UNSUPPORTED"
    safe_message = "The CSV must use UTF-8 encoding."


class CsvDelimiterUndeterminedError(CsvProcessingError):
    code = "CSV_DELIMITER_UNDETERMINED"
    safe_message = "The CSV delimiter could not be determined safely."


class CsvEmptyFileError(CsvProcessingError):
    code = "CSV_EMPTY_FILE"
    safe_message = "The CSV does not contain a header row."


class CsvParseError(CsvProcessingError):
    code = "CSV_PARSE_FAILED"
    safe_message = "The CSV structure could not be parsed."


class CsvFileSizeLimitExceededError(CsvProcessingError):
    code = "CSV_PROCESSING_FILE_SIZE_LIMIT_EXCEEDED"
    safe_message = "The CSV exceeds the configured processing file-size limit."


class CsvRowLimitExceededError(CsvProcessingError):
    code = "CSV_PROCESSING_ROW_LIMIT_EXCEEDED"
    safe_message = "The CSV exceeds the configured data-row limit."


class CsvColumnLimitExceededError(CsvProcessingError):
    code = "CSV_PROCESSING_COLUMN_LIMIT_EXCEEDED"
    safe_message = "The CSV exceeds the configured column limit."


class CsvCellLimitExceededError(CsvProcessingError):
    code = "CSV_PROCESSING_CELL_LIMIT_EXCEEDED"
    safe_message = "The CSV exceeds the configured data-cell limit."


class CsvCellTextLimitExceededError(CsvProcessingError):
    code = "CSV_PROCESSING_CELL_TEXT_LIMIT_EXCEEDED"
    safe_message = "A CSV cell exceeds the configured text limit."


class CsvResultItemTooLargeError(CsvProcessingError):
    code = "CSV_PROCESSING_RESULT_ITEM_TOO_LARGE"
    safe_message = "A CSV result record exceeds the safe persistence size."


class CsvObjectNotFoundError(CsvProcessingError):
    code = "CSV_OBJECT_NOT_FOUND"
    safe_message = "The stored CSV object could not be found."


class CsvObjectStorageError(CsvProcessingError):
    code = "CSV_OBJECT_STORAGE_FAILED"
    safe_message = "The stored CSV object is temporarily unavailable."


class CsvProcessingRepositoryError(Exception):
    """Base error for CSV processing-result persistence failures."""


class CsvProcessingResultAlreadyExistsError(CsvProcessingRepositoryError):
    """Raised when conditional creation finds an existing processing identity."""


class CsvProcessingSerializationError(CsvProcessingRepositoryError):
    """Raised when CSV evidence cannot safely cross the DynamoDB boundary."""


class CsvProcessingResultStorageError(CsvProcessingError):
    code = "CSV_PROCESSING_STORAGE_FAILED"
    safe_message = "The CSV processing result could not be stored."


class InvalidProductSourceCursorError(ProductSourceRepositoryError):
    """Raised when an opaque product-source cursor is invalid."""


class ProductSourceSerializationError(ProductSourceRepositoryError):
    """Raised when source data cannot safely cross the DynamoDB boundary."""


class ProductSourceUploadValidationError(Exception):
    """Base error for safe upload validation failures."""


class InvalidProductSourceFilenameError(ProductSourceUploadValidationError):
    """Raised when multipart filename metadata is absent or unsafe."""


class UnsupportedProductSourceFileTypeError(ProductSourceUploadValidationError):
    """Raised when an upload filename extension is unsupported."""


class ProductSourceMimeTypeMismatchError(ProductSourceUploadValidationError):
    """Raised when declared MIME does not agree with the filename extension."""


class InvalidProductSourceFileContentError(ProductSourceUploadValidationError):
    """Raised when an upload does not match the approved content policy."""


class ObjectStorageError(Exception):
    """Base error for object-storage failures."""


class InvalidObjectKeyError(ObjectStorageError):
    """Raised when a logical object key is unsafe or malformed."""


class UnsupportedObjectExtensionError(ObjectStorageError):
    """Raised when a generated key is requested for an unapproved extension."""


class ObjectAlreadyExistsError(ObjectStorageError):
    """Raised when saving would replace an existing object."""


class ObjectNotFoundError(ObjectStorageError):
    """Raised when an object operation targets no regular stored object."""


class ObjectSizeExceededError(ObjectStorageError):
    """Raised when streamed object bytes exceed the caller's limit."""


class ObjectMetadataError(ObjectStorageError):
    """Raised when stored object metadata is absent, malformed, or inconsistent."""


class ObjectStorageConfigurationError(ObjectStorageError):
    """Raised when object storage cannot be constructed from configuration."""
