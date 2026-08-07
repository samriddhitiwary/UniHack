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
