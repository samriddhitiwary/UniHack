"""Health endpoint response models."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["healthy"]
    service: Literal["catalogiq-api"]
    version: Literal["0.1.0"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    dependencies: dict[Literal["dynamodb"], Literal["available"]]
