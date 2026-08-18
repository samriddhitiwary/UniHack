"""Strict camel-case product-review requests."""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.product_review import AttributeReviewDecisionType
from app.schemas.products.models import to_camel

ReviewerId = str


class ReviewRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
    )


class ProductReviewCreate(ReviewRequest):
    selection_id: UUID


class AttributeReviewDecisionCreate(ReviewRequest):
    version: int = Field(ge=1, strict=True)
    decision_type: AttributeReviewDecisionType
    candidate_id: str | None = Field(default=None, min_length=1, max_length=200)
    manual_value: str | None = Field(default=None, min_length=1, max_length=10_000)
    manual_unit: str | None = Field(default=None, min_length=1, max_length=100)
    reviewer_id: ReviewerId = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:@/-]+$")
    comment: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def fields_match_decision_type(self) -> Self:
        if self.decision_type is AttributeReviewDecisionType.APPROVE_CANDIDATE:
            if (
                self.candidate_id is None
                or self.manual_value is not None
                or self.manual_unit is not None
            ):
                raise ValueError("candidateId is required exclusively for APPROVE_CANDIDATE")
        elif self.decision_type is AttributeReviewDecisionType.APPROVE_PROPOSED:
            if (
                self.candidate_id is not None
                or self.manual_value is not None
                or self.manual_unit is not None
            ):
                raise ValueError("APPROVE_PROPOSED does not accept candidate or manual fields")
        elif self.decision_type is AttributeReviewDecisionType.REJECT_ALL:
            if (
                self.candidate_id is not None
                or self.manual_value is not None
                or self.manual_unit is not None
            ):
                raise ValueError("REJECT_ALL does not accept candidate or manual fields")
        elif self.manual_value is None or self.candidate_id is not None:
            raise ValueError("manualValue is required exclusively for MANUAL_OVERRIDE")
        return self


class ProductReviewComplete(ReviewRequest):
    version: int = Field(ge=1, strict=True)
    reviewer_id: ReviewerId = Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._:@/-]+$")
