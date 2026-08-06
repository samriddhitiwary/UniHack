"""Service liveness and readiness routes."""

import logging
from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.dynamodb import DynamoDBHealth, get_dynamodb_health
from app.schemas.health import HealthResponse, ReadinessResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report that the API process is alive."""
    return HealthResponse(status="healthy", service="catalogiq-api", version="0.1.0")


@router.get("/ready", response_model=ReadinessResponse)
def readiness(
    dynamodb: Annotated[DynamoDBHealth, Depends(get_dynamodb_health)],
) -> ReadinessResponse:
    """Report readiness only when required configuration and DynamoDB are available."""
    try:
        dynamodb.check()
    except (BotoCoreError, ClientError, OSError) as exc:
        logger.warning("DynamoDB readiness check failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "dependencies": {"dynamodb": "unavailable"}},
        ) from exc
    return ReadinessResponse(status="ready", dependencies={"dynamodb": "available"})
