"""Deterministic publishing-readiness precedence and reason normalization."""

from app.core.exceptions import CatalogProjectionReasonLimitExceededError
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)


class CatalogPublishingReadinessEvaluator:
    def __init__(self, *, max_reason_codes: int = 50) -> None:
        self._max_reasons = max_reason_codes

    def evaluate(
        self,
        *,
        blockers: tuple[CatalogBlockingReason, ...],
        warnings: tuple[CatalogWarningReason, ...],
    ) -> tuple[
        CatalogProjectionStatus,
        tuple[CatalogBlockingReason, ...],
        tuple[CatalogWarningReason, ...],
    ]:
        stable_blockers = tuple(dict.fromkeys(blockers))
        stable_warnings = tuple(dict.fromkeys(warnings))
        if len(stable_blockers) + len(stable_warnings) > self._max_reasons:
            raise CatalogProjectionReasonLimitExceededError()
        status = (
            CatalogProjectionStatus.BLOCKED
            if stable_blockers
            else CatalogProjectionStatus.READY_WITH_WARNINGS
            if stable_warnings
            else CatalogProjectionStatus.READY
        )
        return status, stable_blockers, stable_warnings
