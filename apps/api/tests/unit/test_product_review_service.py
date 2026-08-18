"""Review creation, decisions, history, lineage, concurrency, and completion tests."""

from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.exceptions import (
    AttributeSelectionNotFoundForReviewError,
    ProductNotFoundError,
    ProductReviewAlreadyCompletedError,
    ProductReviewAlreadyExistsError,
    ProductReviewAttributeNotFoundError,
    ProductReviewCandidateNotApprovableError,
    ProductReviewCandidateNotFoundError,
    ProductReviewManualOverrideInvalidError,
    ProductReviewRequiredAttributesUnresolvedError,
    ProductReviewSelectionLineageInvalidError,
    ProductReviewVersionConflictError,
)
from app.domain.attribute_selection import AttributeSelectionStatus
from app.domain.product_review import (
    AttributeReviewDecisionType,
    ProductReviewSessionStatus,
    ReviewDecisionPage,
)
from app.schemas.product_review import AttributeReviewDecisionCreate
from app.services.product_review import ProductReviewService
from app.services.review_manual_override import ReviewManualOverride
from tests.fixtures.attribute_normalization import NOW
from tests.unit.test_attribute_selection_engine import attr, pipeline


class One:
    def __init__(self, value, key: str) -> None:
        self.value, self.key = value, key

    def get_by_id(self, identity):
        return self.value if getattr(self.value, self.key) == identity else None


class Schemas:
    def __init__(self, schema) -> None:
        self.schema = schema

    def get_by_category_and_version(self, category, version):
        return (
            self.schema
            if (category, version) == (self.schema.category, self.schema.version)
            else None
        )


class Products:
    def __init__(self, product_id, category) -> None:
        self.product = SimpleNamespace(product_id=product_id, category=category)

    def get_by_id(self, product_id):
        return (
            self.product
            if self.product is not None and product_id == self.product.product_id
            else None
        )


class Reviews:
    def __init__(self) -> None:
        self.review = None
        self.decisions = []
        self.current = {}

    def create(self, review):
        if self.review is not None:
            raise ProductReviewAlreadyExistsError()
        self.review = review
        return review

    def get_by_id(self, review_id):
        return (
            self.review if self.review is not None and self.review.review_id == review_id else None
        )

    def get_by_selection_id(self, selection_id):
        return (
            self.review
            if self.review is not None and self.review.selection_id == selection_id
            else None
        )

    def append_decision(self, review, decision, current, *, expected_version):
        if self.review.version != expected_version:
            raise ProductReviewVersionConflictError()
        self.review = review
        self.decisions.append(decision)
        self.current[current.attribute_name] = current
        return review

    def list_decisions(self, review_id, *, limit, cursor=None):
        return ReviewDecisionPage(tuple(self.decisions[:limit]), None)

    def list_current_decisions(self, review_id):
        return tuple(self.current.values())

    def complete(self, review, *, expected_version):
        if self.review.version != expected_version:
            raise ProductReviewVersionConflictError()
        self.review = review
        return review


def setup(*items):
    schema, normalization, conflict, validation, completeness, selection = pipeline(*items)
    reviews = Reviews()
    service = ProductReviewService(
        product_repository=Products(selection.product_id, selection.category),
        selection_repository=One(selection, "selection_id"),
        conflict_repository=One(conflict, "conflict_detection_id"),
        validation_repository=One(validation, "validation_id"),
        completeness_repository=One(completeness, "completeness_id"),
        normalization_repository=One(normalization, "normalization_id"),
        schema_repository=Schemas(schema),
        review_repository=reviews,
        manual_override=ReviewManualOverride(),
        clock=lambda: NOW,
    )
    review = service.create_review(
        product_id=selection.product_id, selection_id=selection.selection_id
    )
    return service, reviews, review, selection, validation


def request(decision_type, version, **values):
    return AttributeReviewDecisionCreate(
        version=version,
        decision_type=decision_type,
        reviewer_id="reviewer-local-001",
        **values,
    )


def test_create_review_and_duplicate_policy() -> None:
    service, _, review, selection, _ = setup(("voltage", "415", "V"))
    assert review.status is ProductReviewSessionStatus.OPEN and review.version == 1
    assert review.selection_id == selection.selection_id and review.decision_count == 0
    with pytest.raises(ProductReviewAlreadyExistsError):
        service.create_review(product_id=selection.product_id, selection_id=selection.selection_id)


def test_create_rejects_cross_product_and_upstream_lineage_mismatch() -> None:
    schema, normalization, conflict, validation, completeness, selection = pipeline(
        ("voltage", "415", "V")
    )
    service = ProductReviewService(
        product_repository=Products(uuid4(), selection.category),
        selection_repository=One(selection, "selection_id"),
        conflict_repository=One(conflict, "conflict_detection_id"),
        validation_repository=One(replace(validation, extraction_id=uuid4()), "validation_id"),
        completeness_repository=One(completeness, "completeness_id"),
        normalization_repository=One(normalization, "normalization_id"),
        schema_repository=Schemas(schema),
        review_repository=Reviews(),
        manual_override=ReviewManualOverride(),
    )
    with pytest.raises(ProductReviewSelectionLineageInvalidError):
        service.create_review(
            product_id=service._products.product.product_id, selection_id=selection.selection_id
        )


def test_create_requires_product_and_explicit_selection() -> None:
    schema, normalization, conflict, validation, completeness, selection = pipeline(
        ("voltage", "415", "V")
    )
    products = Products(selection.product_id, selection.category)
    products.product = None
    service = ProductReviewService(
        product_repository=products,
        selection_repository=One(selection, "selection_id"),
        conflict_repository=One(conflict, "conflict_detection_id"),
        validation_repository=One(validation, "validation_id"),
        completeness_repository=One(completeness, "completeness_id"),
        normalization_repository=One(normalization, "normalization_id"),
        schema_repository=Schemas(schema),
        review_repository=Reviews(),
        manual_override=ReviewManualOverride(),
    )
    with pytest.raises(ProductNotFoundError):
        service.create_review(product_id=selection.product_id, selection_id=selection.selection_id)
    products.product = SimpleNamespace(product_id=selection.product_id, category=selection.category)
    service._selections = SimpleNamespace(get_by_id=lambda _: None)
    with pytest.raises(AttributeSelectionNotFoundForReviewError):
        service.create_review(product_id=selection.product_id, selection_id=uuid4())


def test_approve_proposed_and_revision_history() -> None:
    service, reviews, review, selection, _ = setup(
        ("ratedPower", "5.5", "kW"), ("ratedPower", "5.5", "kW")
    )
    proposed = service.submit_decision(
        product_id=review.product_id,
        review_id=review.review_id,
        attribute_name="ratedPower",
        request=request(AttributeReviewDecisionType.APPROVE_PROPOSED, 1),
    )
    assert proposed.approved_value == "5.5" and proposed.candidate_id
    rejected = service.submit_decision(
        product_id=review.product_id,
        review_id=review.review_id,
        attribute_name="ratedPower",
        request=request(AttributeReviewDecisionType.REJECT_ALL, 2),
    )
    assert rejected.decision_sequence == 2
    assert len(reviews.decisions) == 2
    assert reviews.current["ratedPower"].decision_id == rejected.decision_id
    assert attr(selection, "ratedPower").selection_status is AttributeSelectionStatus.AUTO_SELECTED


def test_choose_conflicting_and_warning_candidate_but_reject_invalid_candidate() -> None:
    service, _, review, selection, _ = setup(("voltage", "415", "V"), ("voltage", "440", "V"))
    candidate_id = attr(selection, "voltage").review_candidate_ids[1]
    decision = service.submit_decision(
        product_id=review.product_id,
        review_id=review.review_id,
        attribute_name="voltage",
        request=request(
            AttributeReviewDecisionType.APPROVE_CANDIDATE, 1, candidate_id=candidate_id
        ),
    )
    assert decision.approved_value in {"415", "440"}

    service, _, review, selection, _ = setup(("voltage", "415", None))
    warning_id = attr(selection, "voltage").review_candidate_ids[0]
    assert (
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="voltage",
            request=request(
                AttributeReviewDecisionType.APPROVE_CANDIDATE, 1, candidate_id=warning_id
            ),
        ).candidate_id
        == warning_id
    )

    service, _, review, selection, _ = setup(("voltage", "bad", "V"))
    invalid_id = attr(selection, "voltage").review_candidate_ids[0]
    with pytest.raises(ProductReviewCandidateNotApprovableError):
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="voltage",
            request=request(
                AttributeReviewDecisionType.APPROVE_CANDIDATE, 1, candidate_id=invalid_id
            ),
        )


def test_unknown_candidate_stale_version_and_manual_override() -> None:
    service, reviews, review, _, _ = setup(("voltage", "415", "V"))
    with pytest.raises(ProductReviewCandidateNotFoundError):
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="voltage",
            request=request(
                AttributeReviewDecisionType.APPROVE_CANDIDATE,
                1,
                candidate_id="from-another-attribute",
            ),
        )
    with pytest.raises(ProductReviewVersionConflictError):
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="voltage",
            request=request(AttributeReviewDecisionType.REJECT_ALL, 2),
        )
    manual = service.submit_decision(
        product_id=review.product_id,
        review_id=review.review_id,
        attribute_name="voltage",
        request=request(
            AttributeReviewDecisionType.MANUAL_OVERRIDE,
            1,
            manual_value="430",
            manual_unit="V",
            comment="Supplier confirmed",
        ),
    )
    assert (manual.manual_raw_value, manual.approved_value, manual.approved_unit) == (
        "430",
        "430",
        "V",
    )
    assert reviews.review.version == 2


def test_unknown_attribute_and_invalid_manual_override_do_not_mutate_review() -> None:
    service, reviews, review, _, _ = setup(("efficiency", "92", "%"))
    with pytest.raises(ProductReviewAttributeNotFoundError):
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="unknownAttribute",
            request=request(AttributeReviewDecisionType.REJECT_ALL, 1),
        )
    with pytest.raises(ProductReviewManualOverrideInvalidError):
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="efficiency",
            request=request(
                AttributeReviewDecisionType.MANUAL_OVERRIDE,
                1,
                manual_value="105",
                manual_unit="%",
            ),
        )
    assert reviews.review.version == 1 and reviews.decisions == []


def test_reject_all_blocks_required_completion_and_optional_unresolved_is_allowed() -> None:
    required = (
        ("ratedPower", "5.5", "kW"),
        ("voltage", "415", "V"),
        ("frequency", "50", "Hz"),
        ("speedRpm", "1440", "rpm"),
        ("phase", "3", None),
    )
    items = tuple(value for pair in ((item, item) for item in required) for value in pair)
    service, reviews, review, selection, _ = setup(*items)
    version = 1
    for attribute in (item for item in selection.attributes if item.required):
        decision_type = (
            AttributeReviewDecisionType.REJECT_ALL
            if attribute.attribute_name == "voltage"
            else AttributeReviewDecisionType.APPROVE_PROPOSED
        )
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name=attribute.attribute_name,
            request=request(decision_type, version),
        )
        version += 1
    with pytest.raises(ProductReviewRequiredAttributesUnresolvedError):
        service.complete_review(
            product_id=review.product_id,
            review_id=review.review_id,
            version=version,
            reviewer_id="reviewer-local-001",
        )
    service.submit_decision(
        product_id=review.product_id,
        review_id=review.review_id,
        attribute_name="voltage",
        request=request(AttributeReviewDecisionType.APPROVE_PROPOSED, version),
    )
    version += 1
    completed = service.complete_review(
        product_id=review.product_id,
        review_id=review.review_id,
        version=version,
        reviewer_id="reviewer-local-001",
    )
    assert completed.status is ProductReviewSessionStatus.COMPLETED
    assert completed.version == version + 1
    assert all(
        item.attribute_name in reviews.current for item in selection.attributes if item.required
    )
    assert any(
        item.attribute_name not in reviews.current
        for item in selection.attributes
        if not item.required
    )
    with pytest.raises(ProductReviewAlreadyCompletedError):
        service.submit_decision(
            product_id=review.product_id,
            review_id=review.review_id,
            attribute_name="ipRating",
            request=request(AttributeReviewDecisionType.REJECT_ALL, completed.version),
        )
