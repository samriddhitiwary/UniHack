"""Evidence-grounded classification using only reviewed vocabulary and mappings."""

from app.domain.unilog_challenge import (
    ObservedVocabulary,
    UnilogDescriptionSignals,
    UnilogProductClassification,
)
from app.services.unilog_classification.classpath_resolver import UnilogClasspathResolver


class UnilogChallengeClassifier:
    def __init__(self, classpath_resolver: UnilogClasspathResolver | None = None) -> None:
        self._classpaths = classpath_resolver or UnilogClasspathResolver()

    def classify(
        self, signals: UnilogDescriptionSignals, vocabulary: ObservedVocabulary | None
    ) -> UnilogProductClassification:
        del vocabulary
        product = signals.product_type_resolution
        classpath = self._classpaths.resolve(product)
        reasons = tuple(dict.fromkeys((*product.review_reasons, *classpath.review_reasons)))
        evidence: tuple[str, ...] = (
            (f"description-span:{product.evidence_text}",) if product.evidence_text else ()
        )
        if classpath.classpath:
            evidence += (f"verified-classpath:{classpath.mapping_source}",)
        confidences = [value for value in (product.confidence_bp, classpath.confidence_bp) if value]
        return UnilogProductClassification(
            product_type_candidate=product.product_type,
            classpath=classpath.classpath,
            leaf_node=classpath.classpath.rsplit(">", 1)[-1] if classpath.classpath else None,
            confidence_bp=min(confidences) if confidences else 0,
            evidence=evidence,
            review_required=bool(reasons),
            product_family=product.product_family,
            match_method=product.match_method,
            evidence_span=product.evidence_span,
            product_type_confidence_bp=product.confidence_bp,
            classpath_confidence_bp=classpath.confidence_bp,
            review_reasons=reasons,
            department=classpath.department,
            class_name=classpath.class_name,
            fine=classpath.fine,
        )
