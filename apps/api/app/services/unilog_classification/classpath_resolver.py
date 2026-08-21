"""Resolve only verified, general product-type-to-Classpath mappings."""

from app.domain.unilog_classification import (
    ClassificationReviewReason,
    ProductTypeMatchMethod,
    UnilogClassificationVocabulary,
    UnilogClasspathResolution,
    UnilogProductTypeResolution,
)
from app.services.unilog_classification.vocabulary_store import (
    load_default_classification_vocabulary,
)


class UnilogClasspathResolver:
    def __init__(self, vocabulary: UnilogClassificationVocabulary | None = None) -> None:
        value = vocabulary or load_default_classification_vocabulary()
        self._mappings = {item.product_type: item for item in value.verified_classpath_mappings}

    def resolve(self, product_type: UnilogProductTypeResolution) -> UnilogClasspathResolution:
        mapping = self._mappings.get(product_type.product_type or "")
        if mapping is None or product_type.match_method is ProductTypeMatchMethod.MODEL_ASSISTED:
            return UnilogClasspathResolution(
                classpath=None,
                department=None,
                class_name=None,
                fine=None,
                mapping_source=None,
                confidence_bp=0,
                review_required=True,
                review_reasons=(ClassificationReviewReason.CLASSPATH_UNKNOWN,),
            )
        return UnilogClasspathResolution(
            classpath=mapping.classpath,
            department=mapping.department,
            class_name=mapping.class_name,
            fine=mapping.fine,
            mapping_source=mapping.mapping_source,
            confidence_bp=min(product_type.confidence_bp, mapping.confidence_bp),
            review_required=False,
            review_reasons=(),
        )


def resolve_unilog_classpath(
    product_type: UnilogProductTypeResolution,
) -> UnilogClasspathResolution:
    """Resolve one product type through the cached verified mapping index."""

    return UnilogClasspathResolver().resolve(product_type)
