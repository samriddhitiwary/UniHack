import pytest

from app.core.exceptions import CatalogProjectionReasonLimitExceededError
from app.domain.catalog_projection import (
    CatalogBlockingReason,
    CatalogProjectionStatus,
    CatalogWarningReason,
)
from app.services.catalog_publishing_readiness import CatalogPublishingReadinessEvaluator


def test_ready_warning_and_blocked_precedence() -> None:
    evaluator = CatalogPublishingReadinessEvaluator()
    assert evaluator.evaluate(blockers=(), warnings=())[0] is CatalogProjectionStatus.READY
    warning = (CatalogWarningReason.MANUFACTURER_MISSING,)
    assert evaluator.evaluate(blockers=(), warnings=warning) == (
        CatalogProjectionStatus.READY_WITH_WARNINGS,
        (),
        warning,
    )
    blocker = (CatalogBlockingReason.PRODUCT_NAME_MISSING,)
    assert evaluator.evaluate(blockers=blocker, warnings=warning)[0] is (
        CatalogProjectionStatus.BLOCKED
    )


def test_reasons_are_unique_stable_and_bounded() -> None:
    evaluator = CatalogPublishingReadinessEvaluator()
    warning = CatalogWarningReason.DESCRIPTION_MISSING
    assert evaluator.evaluate(blockers=(), warnings=(warning, warning))[2] == (warning,)
    with pytest.raises(CatalogProjectionReasonLimitExceededError):
        CatalogPublishingReadinessEvaluator(max_reason_codes=0).evaluate(
            blockers=(), warnings=(warning,)
        )
