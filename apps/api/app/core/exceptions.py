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


class ProductStatusConflictError(ProductRepositoryError):
    """Raised when a conditional lifecycle mutation finds another Product status."""

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__("product status does not match the expected lifecycle state")


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


class ImageAnalysisError(Exception):
    """Base controlled image-analysis failure with safe job metadata."""

    code = "IMAGE_ANALYSIS_FAILED"
    safe_message = "Image analysis failed."


class InvalidImageAnalysisJobError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_JOB_INVALID"
    safe_message = "The processing job is not eligible for image analysis."


class InvalidImageSourceError(ImageAnalysisError):
    code = "IMAGE_SOURCE_INVALID"
    safe_message = "The processing job does not reference a valid stored image source."


class ImageDecodeError(ImageAnalysisError):
    code = "IMAGE_DECODE_FAILED"
    safe_message = "The image could not be decoded safely."


class ImageFormatUnsupportedError(ImageAnalysisError):
    code = "IMAGE_FORMAT_UNSUPPORTED"
    safe_message = "The decoded image format is unsupported."


class ImageFormatMismatchError(ImageAnalysisError):
    code = "IMAGE_FORMAT_MISMATCH"
    safe_message = "The decoded image format does not match source metadata."


class ImageAnimationNotSupportedError(ImageAnalysisError):
    code = "IMAGE_ANIMATION_NOT_SUPPORTED"
    safe_message = "Animated images are not supported for analysis."


class ImageAnalysisFileSizeLimitExceededError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_FILE_SIZE_LIMIT_EXCEEDED"
    safe_message = "The image exceeds the configured analysis file-size limit."


class ImageAnalysisWidthLimitExceededError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_WIDTH_LIMIT_EXCEEDED"
    safe_message = "The image exceeds the configured width limit."


class ImageAnalysisHeightLimitExceededError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_HEIGHT_LIMIT_EXCEEDED"
    safe_message = "The image exceeds the configured height limit."


class ImageAnalysisPixelLimitExceededError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_PIXEL_LIMIT_EXCEEDED"
    safe_message = "The image exceeds the configured pixel limit."


class ImageAnalysisRegionLimitExceededError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_REGION_LIMIT_EXCEEDED"
    safe_message = "The image exceeds the configured analysis-region limit."


class ImageObjectNotFoundError(ImageAnalysisError):
    code = "IMAGE_OBJECT_NOT_FOUND"
    safe_message = "The stored image object could not be found."


class ImageObjectStorageError(ImageAnalysisError):
    code = "IMAGE_OBJECT_STORAGE_FAILED"
    safe_message = "The stored image object is temporarily unavailable."


class ImageAnalysisRepositoryError(Exception):
    """Base error for image-analysis result persistence failures."""


class ImageAnalysisResultAlreadyExistsError(ImageAnalysisRepositoryError):
    """Raised when conditional creation finds an existing analysis identity."""


class ImageAnalysisSerializationError(ImageAnalysisRepositoryError):
    """Raised when image evidence cannot safely cross the DynamoDB boundary."""


class ImageAnalysisResultStorageError(ImageAnalysisError):
    code = "IMAGE_ANALYSIS_STORAGE_FAILED"
    safe_message = "The image-analysis result could not be stored."


class ImageOcrError(Exception):
    code = "IMAGE_OCR_FAILED"
    safe_message = "The image OCR operation could not be completed."


class InvalidImageOcrJobError(ImageOcrError):
    code = "INVALID_IMAGE_OCR_JOB"
    safe_message = "The processing job is not eligible for image OCR."


class InvalidImageOcrSourceError(ImageOcrError):
    code = "INVALID_IMAGE_OCR_SOURCE"
    safe_message = "The product source is not eligible for image OCR."


class ImageAnalysisResultRequiredError(ImageOcrError):
    code = "IMAGE_ANALYSIS_RESULT_REQUIRED"
    safe_message = "A compatible completed image-analysis result is required."


class ImageOcrEngineUnavailableError(ImageOcrError):
    code = "IMAGE_OCR_ENGINE_UNAVAILABLE"
    safe_message = "The configured local OCR engine is unavailable."


class ImageOcrEngineError(ImageOcrError):
    code = "IMAGE_OCR_ENGINE_FAILED"
    safe_message = "The local OCR engine could not process the image."


class ImageOcrRegionInvalidError(ImageOcrError):
    code = "IMAGE_OCR_REGION_INVALID"
    safe_message = "Image-analysis region evidence is invalid for OCR."


class ImageOcrRegionLimitExceededError(ImageOcrError):
    code = "IMAGE_OCR_REGION_LIMIT_EXCEEDED"
    safe_message = "The OCR region limit was exceeded."


class ImageOcrBlockLimitExceededError(ImageOcrError):
    code = "IMAGE_OCR_BLOCK_LIMIT_EXCEEDED"
    safe_message = "The OCR block limit was exceeded."


class ImageOcrTextLimitExceededError(ImageOcrError):
    code = "IMAGE_OCR_TEXT_LIMIT_EXCEEDED"
    safe_message = "The OCR text limit was exceeded."


class ImageOcrResultItemTooLargeError(ImageOcrError):
    code = "IMAGE_OCR_RESULT_ITEM_TOO_LARGE"
    safe_message = "An OCR evidence record exceeds the safe storage limit."


class ImageOcrObjectNotFoundError(ImageOcrError):
    code = "IMAGE_OCR_OBJECT_NOT_FOUND"
    safe_message = "The stored image object could not be found for OCR."


class ImageOcrObjectStorageError(ImageOcrError):
    code = "IMAGE_OCR_OBJECT_STORAGE_FAILED"
    safe_message = "The stored image object is temporarily unavailable for OCR."


class ImageOcrResultStorageError(ImageOcrError):
    code = "IMAGE_OCR_STORAGE_FAILED"
    safe_message = "The image OCR result could not be stored."


class ImageOcrRepositoryError(Exception):
    """Base error for image OCR result persistence failures."""


class ImageOcrResultAlreadyExistsError(ImageOcrRepositoryError):
    """Raised when conditional creation finds an existing OCR identity."""


class ImageOcrSerializationError(ImageOcrRepositoryError):
    """Raised when OCR evidence cannot safely cross the DynamoDB boundary."""


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


class ProductClassificationError(Exception):
    code = "PRODUCT_CLASSIFICATION_ENGINE_FAILED"
    safe_message = "Product classification could not be completed."


class InvalidProductClassificationJobError(ProductClassificationError):
    code = "INVALID_PRODUCT_CLASSIFICATION_JOB"
    safe_message = "The processing job is not eligible for product classification."


class ProductClassificationProductNotFoundError(ProductClassificationError):
    code = "PRODUCT_CLASSIFICATION_PRODUCT_NOT_FOUND"
    safe_message = "The product required for classification does not exist."


class ProductClassificationEvidenceLimitExceededError(ProductClassificationError):
    code = "PRODUCT_CLASSIFICATION_EVIDENCE_LIMIT_EXCEEDED"
    safe_message = "Product classification evidence exceeds a configured limit."


class ProductClassificationMatchLimitExceededError(ProductClassificationError):
    code = "PRODUCT_CLASSIFICATION_MATCH_LIMIT_EXCEEDED"
    safe_message = "Product classification matches exceed the configured limit."


class ProductClassificationResultItemTooLargeError(ProductClassificationError):
    code = "PRODUCT_CLASSIFICATION_RESULT_ITEM_TOO_LARGE"
    safe_message = "A classification result record exceeds the safe storage limit."


class ProductClassificationResultStorageError(ProductClassificationError):
    code = "PRODUCT_CLASSIFICATION_STORAGE_FAILED"
    safe_message = "The classification result could not be stored."


class ProductClassificationRepositoryError(Exception):
    """Base error for classification-result persistence failures."""


class ProductClassificationResultAlreadyExistsError(ProductClassificationRepositoryError):
    """Raised when conditional creation finds an existing classification identity."""


class ProductClassificationSerializationError(ProductClassificationRepositoryError):
    """Raised when classification records cannot safely cross persistence."""


class CategoryAttributeSchemaError(Exception):
    code = "CATEGORY_ATTRIBUTE_SCHEMA_FAILED"
    safe_message = "The category attribute schema operation could not be completed."


class CategoryAttributeSchemaNotAvailableError(CategoryAttributeSchemaError):
    code = "CATEGORY_ATTRIBUTE_SCHEMA_NOT_AVAILABLE"
    safe_message = "No category attribute schema is available."


class CategoryAttributeSchemaValidationError(CategoryAttributeSchemaError):
    code = "CATEGORY_ATTRIBUTE_SCHEMA_INVALID"
    safe_message = "The category attribute schema is invalid."


class CategoryAttributeAliasConflictError(CategoryAttributeSchemaValidationError):
    code = "CATEGORY_ATTRIBUTE_ALIAS_CONFLICT"
    safe_message = "A category attribute alias maps to more than one attribute."


class CategoryAttributeSchemaVersionDriftError(CategoryAttributeSchemaError):
    code = "CATEGORY_ATTRIBUTE_SCHEMA_VERSION_DRIFT"
    safe_message = "A persisted schema version differs from the built-in immutable version."


class CategoryAttributeSchemaItemTooLargeError(CategoryAttributeSchemaError):
    code = "CATEGORY_ATTRIBUTE_SCHEMA_ITEM_TOO_LARGE"
    safe_message = "The category attribute schema exceeds the safe storage limit."


class CategoryAttributeSchemaRepositoryError(Exception):
    """Base error for category-attribute-schema persistence failures."""


class CategoryAttributeSchemaAlreadyExistsError(CategoryAttributeSchemaRepositoryError):
    """Raised when an immutable category/version already exists or conflicts."""


class CategoryAttributeSchemaSerializationError(CategoryAttributeSchemaRepositoryError):
    """Raised when schema data cannot safely cross the persistence boundary."""


class StructuredAttributeExtractionError(Exception):
    code = "ATTRIBUTE_EXTRACTION_FAILED"
    safe_message = "Structured attribute extraction could not be completed."


class InvalidStructuredAttributeExtractionJobError(StructuredAttributeExtractionError):
    code = "INVALID_ATTRIBUTE_EXTRACTION_JOB"
    safe_message = "The processing job is not eligible for attribute extraction."


class StructuredAttributeExtractionPrerequisiteError(StructuredAttributeExtractionError):
    code = "ATTRIBUTE_EXTRACTION_PREREQUISITE_FAILED"
    safe_message = "Attribute extraction prerequisites are not available."


class StructuredAttributeExtractionLimitExceededError(StructuredAttributeExtractionError):
    code = "ATTRIBUTE_EXTRACTION_LIMIT_EXCEEDED"
    safe_message = "Attribute extraction exceeds a configured limit."


class StructuredAttributeExtractionResultStorageError(StructuredAttributeExtractionError):
    code = "ATTRIBUTE_EXTRACTION_STORAGE_FAILED"
    safe_message = "The attribute extraction result could not be stored."


class StructuredAttributeExtractionResultItemTooLargeError(StructuredAttributeExtractionError):
    code = "ATTRIBUTE_EXTRACTION_RESULT_ITEM_TOO_LARGE"
    safe_message = "An attribute extraction record exceeds the safe storage limit."


class StructuredAttributeExtractionRepositoryError(Exception):
    """Base error for structured-attribute result persistence failures."""


class StructuredAttributeExtractionResultAlreadyExistsError(
    StructuredAttributeExtractionRepositoryError
):
    """Raised when conditional creation finds an existing extraction identity."""


class StructuredAttributeExtractionSerializationError(StructuredAttributeExtractionRepositoryError):
    """Raised when extraction records cannot safely cross persistence."""


class AttributeNormalizationError(Exception):
    code = "ATTRIBUTE_NORMALIZATION_ENGINE_FAILED"
    safe_message = "Attribute normalization could not be completed."


class InvalidAttributeNormalizationJobError(AttributeNormalizationError):
    code = "INVALID_ATTRIBUTE_NORMALIZATION_JOB"
    safe_message = "The processing job is not eligible for attribute normalization."


class AttributeNormalizationExtractionRequiredError(AttributeNormalizationError):
    code = "ATTRIBUTE_NORMALIZATION_EXTRACTION_REQUIRED"
    safe_message = "The required attribute extraction result is unavailable."


class AttributeNormalizationSchemaNotAvailableError(AttributeNormalizationError):
    code = "ATTRIBUTE_NORMALIZATION_SCHEMA_NOT_AVAILABLE"
    safe_message = "The exact attribute schema is unavailable for normalization."


class AttributeNormalizationSchemaMismatchError(AttributeNormalizationError):
    code = "ATTRIBUTE_NORMALIZATION_SCHEMA_MISMATCH"
    safe_message = "The attribute schema fingerprint does not match extraction lineage."


class AttributeNormalizationCandidateLimitExceededError(AttributeNormalizationError):
    code = "ATTRIBUTE_NORMALIZATION_CANDIDATE_LIMIT_EXCEEDED"
    safe_message = "Attribute normalization candidates exceed a configured limit."


class AttributeNormalizationResultItemTooLargeError(AttributeNormalizationError):
    code = "ATTRIBUTE_NORMALIZATION_RESULT_ITEM_TOO_LARGE"
    safe_message = "An attribute normalization record exceeds the safe storage limit."


class AttributeNormalizationResultStorageError(AttributeNormalizationError):
    code = "ATTRIBUTE_NORMALIZATION_STORAGE_FAILED"
    safe_message = "The attribute normalization result could not be stored."


class AttributeNormalizationRepositoryError(Exception):
    """Base error for attribute-normalization persistence failures."""


class AttributeNormalizationResultAlreadyExistsError(AttributeNormalizationRepositoryError):
    """Raised when a conditional normalization create finds existing data."""


class AttributeNormalizationSerializationError(AttributeNormalizationRepositoryError):
    """Raised when a normalization partition is malformed or incomplete."""


class AttributeConflictDetectionError(Exception):
    code = "ATTRIBUTE_CONFLICT_ENGINE_FAILED"
    safe_message = "Attribute conflict detection could not be completed."


class InvalidAttributeConflictDetectionJobError(AttributeConflictDetectionError):
    code = "INVALID_ATTRIBUTE_CONFLICT_DETECTION_JOB"
    safe_message = "The processing job is not eligible for conflict detection."


class AttributeConflictNormalizationRequiredError(AttributeConflictDetectionError):
    code = "ATTRIBUTE_CONFLICT_NORMALIZATION_REQUIRED"
    safe_message = "The required attribute normalization result is unavailable."


class AttributeConflictCrossProductLineageError(AttributeConflictDetectionError):
    code = "ATTRIBUTE_CONFLICT_CROSS_PRODUCT_LINEAGE"
    safe_message = "The normalization result does not belong to this product."


class AttributeConflictLimitExceededError(AttributeConflictDetectionError):
    code = "ATTRIBUTE_CONFLICT_LIMIT_EXCEEDED"
    safe_message = "Attribute conflict detection exceeds a configured limit."


class AttributeConflictAttributeLimitExceededError(AttributeConflictLimitExceededError):
    code = "ATTRIBUTE_CONFLICT_ATTRIBUTE_LIMIT_EXCEEDED"


class AttributeConflictCandidateLimitExceededError(AttributeConflictLimitExceededError):
    code = "ATTRIBUTE_CONFLICT_CANDIDATE_LIMIT_EXCEEDED"


class AttributeConflictGroupLimitExceededError(AttributeConflictLimitExceededError):
    code = "ATTRIBUTE_CONFLICT_GROUP_LIMIT_EXCEEDED"


class AttributeConflictResultItemTooLargeError(AttributeConflictDetectionError):
    code = "ATTRIBUTE_CONFLICT_RESULT_ITEM_TOO_LARGE"
    safe_message = "An attribute conflict record exceeds the safe storage limit."


class AttributeConflictResultStorageError(AttributeConflictDetectionError):
    code = "ATTRIBUTE_CONFLICT_STORAGE_FAILED"
    safe_message = "The attribute conflict detection result could not be stored."


class AttributeConflictRepositoryError(Exception):
    """Base error for attribute-conflict persistence failures."""


class AttributeConflictResultAlreadyExistsError(AttributeConflictRepositoryError):
    """Raised when conditional creation finds an existing result."""


class AttributeConflictSerializationError(AttributeConflictRepositoryError):
    """Raised when a conflict result partition is incomplete or malformed."""


class AttributeCompletenessError(Exception):
    code = "ATTRIBUTE_COMPLETENESS_ENGINE_FAILED"
    safe_message = "Attribute completeness evaluation could not be completed."


class InvalidAttributeCompletenessJobError(AttributeCompletenessError):
    code = "INVALID_ATTRIBUTE_COMPLETENESS_JOB"
    safe_message = "The processing job is not eligible for completeness evaluation."


class AttributeCompletenessConflictResultRequiredError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_CONFLICT_RESULT_REQUIRED"
    safe_message = "The required conflict-detection result is unavailable."


class AttributeCompletenessCrossProductLineageError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_CROSS_PRODUCT_LINEAGE"
    safe_message = "The conflict-detection result does not belong to this product."


class AttributeCompletenessSchemaNotAvailableError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_SCHEMA_NOT_AVAILABLE"
    safe_message = "The exact category schema is unavailable for completeness evaluation."


class AttributeCompletenessSchemaMismatchError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_SCHEMA_MISMATCH"
    safe_message = "The category schema fingerprint does not match completeness lineage."


class AttributeCompletenessAttributeLimitExceededError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_ATTRIBUTE_LIMIT_EXCEEDED"
    safe_message = "Completeness attributes exceed the configured limit."


class AttributeCompletenessCandidateIdLimitExceededError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_CANDIDATE_ID_LIMIT_EXCEEDED"
    safe_message = "Completeness candidate identifiers exceed the configured limit."


class AttributeCompletenessResultItemTooLargeError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_RESULT_ITEM_TOO_LARGE"
    safe_message = "An attribute completeness record exceeds the safe storage limit."


class AttributeCompletenessResultStorageError(AttributeCompletenessError):
    code = "ATTRIBUTE_COMPLETENESS_STORAGE_FAILED"
    safe_message = "The attribute completeness result could not be stored."


class AttributeCompletenessRepositoryError(Exception):
    """Base error for attribute-completeness persistence failures."""


class AttributeCompletenessResultAlreadyExistsError(AttributeCompletenessRepositoryError):
    """Raised when conditional creation finds an existing result."""


class AttributeCompletenessSerializationError(AttributeCompletenessRepositoryError):
    """Raised when a completeness partition is incomplete or malformed."""


class AttributeValidationError(Exception):
    code = "ATTRIBUTE_VALIDATION_ENGINE_FAILED"
    safe_message = "Attribute validation could not be completed."


class InvalidAttributeValidationJobError(AttributeValidationError):
    code = "INVALID_ATTRIBUTE_VALIDATION_JOB"
    safe_message = "The processing job is not eligible for attribute validation."


class AttributeValidationNormalizationRequiredError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_NORMALIZATION_REQUIRED"
    safe_message = "The required normalization result is unavailable."


class AttributeValidationCrossProductLineageError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_CROSS_PRODUCT_LINEAGE"
    safe_message = "The normalization result does not belong to this product."


class AttributeValidationSchemaNotAvailableError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_SCHEMA_NOT_AVAILABLE"
    safe_message = "The exact category schema is unavailable for attribute validation."


class AttributeValidationSchemaMismatchError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_SCHEMA_MISMATCH"
    safe_message = "The category schema fingerprint does not match validation lineage."


class AttributeValidationUnknownAttributeError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_UNKNOWN_ATTRIBUTE"
    safe_message = "A normalized candidate references an unknown schema attribute."


class AttributeValidationSchemaRuleInvalidError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_SCHEMA_RULE_INVALID"
    safe_message = "An attribute schema validation rule is invalid."


class AttributeValidationCandidateLimitExceededError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_CANDIDATE_LIMIT_EXCEEDED"
    safe_message = "Validation candidates exceed the configured limit."


class AttributeValidationAttributeLimitExceededError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_ATTRIBUTE_LIMIT_EXCEEDED"
    safe_message = "Validation attributes exceed the configured limit."


class AttributeValidationValueLimitExceededError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_VALUE_LIMIT_EXCEEDED"
    safe_message = "A validation value exceeds the configured limit."


class AttributeValidationIssueLimitExceededError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_ISSUE_LIMIT_EXCEEDED"
    safe_message = "Validation issues exceed the configured limit."


class AttributeValidationResultItemTooLargeError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_RESULT_ITEM_TOO_LARGE"
    safe_message = "An attribute validation record exceeds the safe storage limit."


class AttributeValidationResultStorageError(AttributeValidationError):
    code = "ATTRIBUTE_VALIDATION_STORAGE_FAILED"
    safe_message = "The attribute validation result could not be stored."


class AttributeValidationRepositoryError(Exception):
    """Base error for attribute-validation persistence failures."""


class AttributeValidationResultAlreadyExistsError(AttributeValidationRepositoryError):
    """Raised when conditional creation finds an existing result."""


class AttributeValidationSerializationError(AttributeValidationRepositoryError):
    """Raised when a validation partition is incomplete or malformed."""


class AttributeSelectionError(Exception):
    code = "ATTRIBUTE_SELECTION_ENGINE_FAILED"
    safe_message = "Attribute selection could not be completed."


class InvalidAttributeSelectionJobError(AttributeSelectionError):
    code = "INVALID_ATTRIBUTE_SELECTION_JOB"
    safe_message = "The processing job is not eligible for attribute selection."


class AttributeSelectionConflictResultRequiredError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_CONFLICT_RESULT_REQUIRED"
    safe_message = "The required conflict result is unavailable."


class AttributeSelectionValidationResultRequiredError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_VALIDATION_RESULT_REQUIRED"
    safe_message = "The required validation result is unavailable."


class AttributeSelectionCompletenessResultRequiredError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_COMPLETENESS_RESULT_REQUIRED"
    safe_message = "The required completeness result is unavailable."


class AttributeSelectionNormalizationRequiredError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_NORMALIZATION_REQUIRED"
    safe_message = "The required normalization result is unavailable."


class AttributeSelectionCrossProductLineageError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_CROSS_PRODUCT_LINEAGE"
    safe_message = "Selection inputs do not belong to the same product."


class AttributeSelectionLineageMismatchError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_LINEAGE_MISMATCH"
    safe_message = "Selection input lineage does not match."


class AttributeSelectionAttributeLimitExceededError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_ATTRIBUTE_LIMIT_EXCEEDED"
    safe_message = "Selection attributes exceed the configured limit."


class AttributeSelectionCandidateLimitExceededError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_CANDIDATE_LIMIT_EXCEEDED"
    safe_message = "Selection candidate identifiers exceed the configured limit."


class AttributeSelectionReasonLimitExceededError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_REASON_LIMIT_EXCEEDED"
    safe_message = "Selection reason codes exceed the configured limit."


class AttributeSelectionResultItemTooLargeError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_RESULT_ITEM_TOO_LARGE"
    safe_message = "An attribute selection record exceeds the safe storage limit."


class AttributeSelectionResultStorageError(AttributeSelectionError):
    code = "ATTRIBUTE_SELECTION_STORAGE_FAILED"
    safe_message = "The attribute selection result could not be stored."


class AttributeSelectionRepositoryError(Exception):
    """Base error for attribute-selection persistence failures."""


class AttributeSelectionResultAlreadyExistsError(AttributeSelectionRepositoryError):
    """Raised when conditional creation finds an existing result."""


class AttributeSelectionSerializationError(AttributeSelectionRepositoryError):
    """Raised when a selection partition is incomplete or malformed."""


class ProductReviewError(Exception):
    """Base safe review-domain failure."""

    code = "REVIEW_OPERATION_FAILED"
    safe_message = "The review operation could not be completed."
    status_code = 422
    details: dict[str, object]

    def __init__(self, *, details: dict[str, object] | None = None) -> None:
        self.details = details or {}
        super().__init__(self.safe_message)


class AttributeSelectionNotFoundForReviewError(ProductReviewError):
    code = "ATTRIBUTE_SELECTION_NOT_FOUND"
    safe_message = "The requested attribute selection does not exist."
    status_code = 404


class ProductReviewNotFoundError(ProductReviewError):
    code = "REVIEW_NOT_FOUND"
    safe_message = "The requested product review does not exist."
    status_code = 404


class ProductReviewAttributeNotFoundError(ProductReviewError):
    code = "ATTRIBUTE_NOT_IN_SELECTION"
    safe_message = "The requested attribute is not part of the review selection."
    status_code = 404


class ProductReviewCandidateNotFoundError(ProductReviewError):
    code = "REVIEW_CANDIDATE_NOT_FOUND"
    safe_message = "The requested candidate does not belong to this attribute review."
    status_code = 404


class ProductReviewAlreadyExistsError(ProductReviewError):
    code = "REVIEW_ALREADY_EXISTS_FOR_SELECTION"
    safe_message = "A review already exists for this attribute selection."
    status_code = 409


class ProductReviewVersionConflictError(ProductReviewError):
    code = "REVIEW_VERSION_CONFLICT"
    safe_message = "The review version is stale. Retrieve the review and try again."
    status_code = 409


class ProductReviewAlreadyCompletedError(ProductReviewError):
    code = "REVIEW_ALREADY_COMPLETED"
    safe_message = "The completed review cannot be changed."
    status_code = 409


class ProductReviewRequiredAttributesUnresolvedError(ProductReviewError):
    code = "REVIEW_REQUIRED_ATTRIBUTES_UNRESOLVED"
    safe_message = "Required review attributes remain unresolved."
    status_code = 409


class ProductReviewSelectionLineageInvalidError(ProductReviewError):
    code = "REVIEW_SELECTION_LINEAGE_INVALID"
    safe_message = "The review selection lineage is invalid."
    status_code = 422


class ProductReviewDecisionNotAllowedError(ProductReviewError):
    code = "REVIEW_DECISION_NOT_ALLOWED"
    safe_message = "The requested review decision is not allowed."
    status_code = 422


class ProductReviewCandidateNotApprovableError(ProductReviewError):
    code = "REVIEW_CANDIDATE_NOT_APPROVABLE"
    safe_message = "The requested candidate is not approvable."
    status_code = 422


class ProductReviewManualOverrideInvalidError(ProductReviewError):
    code = "REVIEW_MANUAL_OVERRIDE_INVALID"
    safe_message = "The manual override does not satisfy the attribute schema."
    status_code = 422


class ProductReviewDecisionLimitExceededError(ProductReviewError):
    code = "REVIEW_DECISION_LIMIT_EXCEEDED"
    safe_message = "The review exceeds the configured decision limit."
    status_code = 422


class ProductReviewItemTooLargeError(ProductReviewError):
    code = "REVIEW_ITEM_TOO_LARGE"
    safe_message = "A product-review record exceeds the safe storage limit."
    status_code = 422


class InvalidProductReviewCursorError(ProductReviewError):
    code = "INVALID_REVIEW_CURSOR"
    safe_message = "The review decision cursor is invalid."
    status_code = 400


class ProductReviewRepositoryError(Exception):
    """Base product-review persistence failure."""


class ProductReviewSerializationError(ProductReviewRepositoryError):
    """Raised for malformed or inconsistent review partitions."""


class ReviewedAttributeMaterializationError(Exception):
    code = "REVIEWED_MATERIALIZATION_ENGINE_FAILED"
    safe_message = "Reviewed attribute materialization could not be completed."


class InvalidReviewedAttributeMaterializationJobError(ReviewedAttributeMaterializationError):
    code = "INVALID_REVIEWED_ATTRIBUTE_MATERIALIZATION_JOB"
    safe_message = "The processing job is not eligible for reviewed attribute materialization."


class ReviewedMaterializationReviewRequiredError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_REVIEW_REQUIRED"
    safe_message = "The required product review is unavailable."


class ReviewedMaterializationReviewNotCompletedError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_REVIEW_NOT_COMPLETED"
    safe_message = "The product review must be completed before materialization."


class ReviewedMaterializationCrossProductLineageError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_CROSS_PRODUCT_LINEAGE"
    safe_message = "The review does not belong to the materialization product."


class ReviewedMaterializationLineageMismatchError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_LINEAGE_MISMATCH"
    safe_message = "Reviewed materialization lineage is inconsistent."


class ReviewedMaterializationSchemaNotAvailableError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_SCHEMA_NOT_AVAILABLE"
    safe_message = "The exact reviewed attribute schema is unavailable."


class ReviewedMaterializationSchemaMismatchError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_SCHEMA_MISMATCH"
    safe_message = "The reviewed attribute schema fingerprint does not match."


class ReviewedMaterializationReviewStateInvalidError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_REVIEW_STATE_INVALID"
    safe_message = "The current review state is inconsistent."


class ReviewedMaterializationRequiredAttributeUnresolvedError(
    ReviewedAttributeMaterializationError
):
    code = "REVIEWED_MATERIALIZATION_REQUIRED_ATTRIBUTE_UNRESOLVED"
    safe_message = "A required reviewed attribute remains unresolved."


class ReviewedMaterializationUnknownAttributeError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_UNKNOWN_ATTRIBUTE"
    safe_message = "The review contains an attribute absent from the exact schema."


class ReviewedMaterializationDecisionInvalidError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_DECISION_INVALID"
    safe_message = "A current review decision cannot be materialized."


class ReviewedMaterializationAlreadyExistsError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_ALREADY_EXISTS"
    safe_message = "A reviewed materialization already exists for this review."


class ReviewedMaterializationAttributeLimitExceededError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_ATTRIBUTE_LIMIT_EXCEEDED"
    safe_message = "Reviewed attributes exceed the configured limit."


class ReviewedMaterializationResultItemTooLargeError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_RESULT_ITEM_TOO_LARGE"
    safe_message = "A reviewed materialization record exceeds the safe storage limit."


class ReviewedMaterializationResultStorageError(ReviewedAttributeMaterializationError):
    code = "REVIEWED_MATERIALIZATION_STORAGE_FAILED"
    safe_message = "The reviewed attribute result could not be stored."


class ReviewedAttributeRepositoryError(Exception):
    """Base reviewed-attribute result persistence failure."""


class ReviewedAttributeSerializationError(ReviewedAttributeRepositoryError):
    """Raised when a reviewed-attribute partition is malformed or incomplete."""


class CatalogProjectionError(Exception):
    code = "CATALOG_PROJECTION_ENGINE_FAILED"
    safe_message = "The commerce catalog projection could not be completed."


class InvalidCatalogProjectionJobError(CatalogProjectionError):
    code = "INVALID_CATALOG_PROJECTION_JOB"
    safe_message = "The processing job is not eligible for catalog projection."


class CatalogProjectionProductRequiredError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_PRODUCT_REQUIRED"
    safe_message = "The catalog projection Product is unavailable."


class CatalogProjectionMaterializationRequiredError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_REVIEWED_ATTRIBUTES_MISSING"
    safe_message = "The required reviewed attribute materialization is unavailable."


class CatalogProjectionCrossProductLineageError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_CROSS_PRODUCT_LINEAGE"
    safe_message = "The reviewed materialization does not belong to the projection Product."


class CatalogProjectionCategoryMismatchError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_CATEGORY_MISMATCH"
    safe_message = "Product and reviewed materialization categories do not match."


class CatalogProjectionLineageInvalidError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_LINEAGE_INVALID"
    safe_message = "Reviewed attribute lineage is inconsistent."


class CatalogProjectionRequiredAttributesIncompleteError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_REQUIRED_ATTRIBUTES_INCOMPLETE"
    safe_message = "Required reviewed attributes are incomplete."


class CatalogProjectionAlreadyExistsError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_ALREADY_EXISTS"
    safe_message = "A catalog projection already exists for this materialization."


class CatalogProjectionAttributeLimitExceededError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_ATTRIBUTE_LIMIT_EXCEEDED"
    safe_message = "Catalog projection attributes exceed the configured limit."


class CatalogProjectionReasonLimitExceededError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_REASON_LIMIT_EXCEEDED"
    safe_message = "Catalog projection reason codes exceed the configured limit."


class CatalogProjectionProductTextLimitExceededError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_PRODUCT_TEXT_LIMIT_EXCEEDED"
    safe_message = "Catalog projection Product identity exceeds the configured limit."


class CatalogProjectionValueLimitExceededError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_VALUE_LIMIT_EXCEEDED"
    safe_message = "A catalog projection attribute value exceeds the configured limit."


class CatalogProjectionResultItemTooLargeError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_RESULT_ITEM_TOO_LARGE"
    safe_message = "A catalog projection record exceeds the safe storage limit."


class CatalogProjectionResultStorageError(CatalogProjectionError):
    code = "CATALOG_PROJECTION_STORAGE_FAILED"
    safe_message = "The commerce catalog projection could not be stored."


class CatalogProjectionRepositoryError(Exception):
    """Base commerce catalog projection persistence failure."""


class CatalogProjectionSerializationError(CatalogProjectionRepositoryError):
    """Raised when a catalog projection partition is malformed or incomplete."""


class PublishingReadinessError(Exception):
    """Base controlled error for publishing-readiness API operations."""

    status_code = 409
    code = "PUBLISHING_READINESS_FAILED"
    safe_message = "Publishing readiness could not be applied."

    @property
    def details(self) -> dict[str, object]:
        return {}


class CatalogProjectionNotFoundError(PublishingReadinessError):
    status_code = 404
    code = "CATALOG_PROJECTION_NOT_FOUND"
    safe_message = "The requested catalog projection does not exist."

    def __init__(self, projection_id: UUID | str) -> None:
        self.projection_id = str(projection_id)
        super().__init__(self.safe_message)

    @property
    def details(self) -> dict[str, object]:
        return {"projectionId": self.projection_id}


class PublishingReadinessCrossProductProjectionError(PublishingReadinessError):
    status_code = 422
    code = "PUBLISHING_READINESS_CROSS_PRODUCT_PROJECTION"
    safe_message = "The catalog projection does not belong to the requested product."


class PublishingReadinessBlockedError(PublishingReadinessError):
    code = "PUBLISHING_READINESS_BLOCKED"
    safe_message = "The catalog projection contains publishing-readiness blockers."

    def __init__(self, blocking_reason_codes: tuple[str, ...]) -> None:
        self.blocking_reason_codes = blocking_reason_codes
        super().__init__(self.safe_message)

    @property
    def details(self) -> dict[str, object]:
        return {"blockingReasonCodes": list(self.blocking_reason_codes)}


class PublishingReadinessProductChangedError(PublishingReadinessError):
    code = "PUBLISHING_READINESS_PRODUCT_CHANGED"
    safe_message = "The product has changed since this catalog projection was created."


class PublishingReadinessStatusTransitionNotAllowedError(PublishingReadinessError):
    code = "PUBLISHING_READINESS_STATUS_TRANSITION_NOT_ALLOWED"
    safe_message = "The product status does not allow publishing readiness to be applied."

    def __init__(self, current_status: str) -> None:
        self.current_status = current_status
        super().__init__(self.safe_message)

    @property
    def details(self) -> dict[str, object]:
        return {"currentStatus": self.current_status}


class ProductAlreadyReadyToPublishError(PublishingReadinessError):
    code = "PRODUCT_ALREADY_READY_TO_PUBLISH"
    safe_message = "The product is already ready to publish."


class CatalogExportError(Exception):
    code = "CATALOG_EXPORT_ENGINE_FAILED"
    safe_message = "The catalog export could not be completed."


class InvalidCatalogExportJobError(CatalogExportError):
    code = "INVALID_CATALOG_EXPORT_JOB"
    safe_message = "The processing job is not eligible for catalog export."


class CatalogExportProductRequiredError(CatalogExportError):
    code = "CATALOG_EXPORT_PRODUCT_REQUIRED"
    safe_message = "The catalog export Product is unavailable."


class CatalogExportProjectionRequiredError(CatalogExportError):
    code = "CATALOG_EXPORT_PROJECTION_REQUIRED"
    safe_message = "The required catalog projection is unavailable."


class CatalogExportCrossProductProjectionError(CatalogExportError):
    code = "CATALOG_EXPORT_CROSS_PRODUCT_PROJECTION"
    safe_message = "The catalog projection does not belong to the export Product."


class CatalogExportProjectionBlockedError(CatalogExportError):
    code = "CATALOG_EXPORT_PROJECTION_BLOCKED"
    safe_message = "A blocked catalog projection cannot be exported."


class CatalogExportLineageInvalidError(CatalogExportError):
    code = "CATALOG_EXPORT_LINEAGE_INVALID"
    safe_message = "Catalog export lineage is inconsistent."


class CatalogExportAlreadyExistsError(CatalogExportError):
    code = "CATALOG_EXPORT_ALREADY_EXISTS"
    safe_message = "An authoritative export already exists for this catalog projection."


class CatalogExportAttributeLimitExceededError(CatalogExportError):
    code = "CATALOG_EXPORT_ATTRIBUTE_LIMIT_EXCEEDED"
    safe_message = "Catalog export attributes exceed the configured limit."


class CatalogExportJsonSizeLimitExceededError(CatalogExportError):
    code = "CATALOG_EXPORT_JSON_SIZE_LIMIT_EXCEEDED"
    safe_message = "The canonical JSON export exceeds the configured limit."


class CatalogExportCsvSizeLimitExceededError(CatalogExportError):
    code = "CATALOG_EXPORT_CSV_SIZE_LIMIT_EXCEEDED"
    safe_message = "The catalog CSV export exceeds the configured limit."


class CatalogExportManifestSizeLimitExceededError(CatalogExportError):
    code = "CATALOG_EXPORT_MANIFEST_SIZE_LIMIT_EXCEEDED"
    safe_message = "The catalog export manifest exceeds the configured limit."


class CatalogExportSerializationError(CatalogExportError):
    code = "CATALOG_EXPORT_SERIALIZATION_FAILED"
    safe_message = "A catalog export artifact could not be serialized."


class CatalogExportStorageError(CatalogExportError):
    code = "CATALOG_EXPORT_STORAGE_FAILED"
    safe_message = "Catalog export artifacts could not be stored."


class CatalogExportResultItemTooLargeError(CatalogExportError):
    code = "CATALOG_EXPORT_RESULT_ITEM_TOO_LARGE"
    safe_message = "A catalog export result record exceeds the safe persistence size."


class CatalogExportResultStorageError(CatalogExportError):
    code = "CATALOG_EXPORT_RESULT_STORAGE_FAILED"
    safe_message = "Catalog export result metadata could not be stored."


class CatalogExportRepositoryError(Exception):
    """Base catalog-export result persistence failure."""


class CatalogExportResultSerializationError(CatalogExportRepositoryError):
    """Raised when a catalog-export result partition is malformed or incomplete."""
