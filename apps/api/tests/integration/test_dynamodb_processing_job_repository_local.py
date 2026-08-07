"""Opt-in DynamoDB Local contract test for processing-job persistence."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.api.dependencies.dynamodb import create_dynamodb_client
from app.core.config import get_settings
from app.core.exceptions import ProcessingJobVersionConflictError
from app.domain.processing_jobs import (
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingJobType,
    transition_processing_job,
)
from app.repositories.dynamodb_processing_jobs import DynamoDBProcessingJobRepository
from app.utils.dynamodb import serialize_item

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DYNAMODB_INTEGRATION") != "1",
    reason="set RUN_DYNAMODB_INTEGRATION=1 after creating the processing-jobs table",
)


def test_processing_job_repository_contract_against_dynamodb_local() -> None:
    settings = get_settings()
    client = create_dynamodb_client(settings)
    table_name = settings.table_name("processing-jobs")
    repository = DynamoDBProcessingJobRepository(client, table_name)
    product_id, source_id = uuid4(), uuid4()
    created = datetime.now(UTC) - timedelta(seconds=2)
    first = ProcessingJob.create(
        product_id=product_id,
        source_id=source_id,
        job_type=ProcessingJobType.SOURCE_PROCESSING,
        now=created,
    )
    second = ProcessingJob.create(
        product_id=product_id,
        source_id=source_id,
        job_type=ProcessingJobType.PDF_TEXT_EXTRACTION,
        now=created + timedelta(seconds=1),
    )
    try:
        repository.create(first)
        repository.create(second)
        assert repository.get_by_id(first.job_id) == first
        assert [job.job_id for job in repository.list_by_product(product_id).items] == [
            second.job_id,
            first.job_id,
        ]
        assert [job.job_id for job in repository.list_by_source(product_id, source_id).items] == [
            second.job_id,
            first.job_id,
        ]
        running = transition_processing_job(first, ProcessingJobStatus.RUNNING)
        updated = repository.update(running, expected_version=1)
        assert updated.version == 2 and updated.started_at is not None
        with pytest.raises(ProcessingJobVersionConflictError):
            repository.update(running, expected_version=1)
    finally:
        for job in (first, second):
            client.delete_item(TableName=table_name, Key=serialize_item({"jobId": job.job_id}))
