"""Observed-taxonomy-constrained challenge classifier."""

from app.domain.unilog_challenge import (
    ObservedVocabulary,
    UnilogDescriptionSignals,
    UnilogProductClassification,
)

_DISHWASHER_LEAF = "Built-In Dishwashers"


class UnilogChallengeClassifier:
    def classify(
        self, signals: UnilogDescriptionSignals, vocabulary: ObservedVocabulary | None
    ) -> UnilogProductClassification:
        product_type = signals.product_type
        matching = (
            ()
            if vocabulary is None or product_type != "Dishwasher"
            else tuple(
                path for path in sorted(vocabulary.classpaths) if path.endswith(_DISHWASHER_LEAF)
            )
        )
        if len(matching) == 1:
            return UnilogProductClassification(
                product_type_candidate=product_type,
                classpath=matching[0],
                leaf_node=_DISHWASHER_LEAF,
                confidence_bp=9_000,
                evidence=(
                    "explicit-product-type:Dishwasher",
                    "official-labelled-classpath-pattern",
                ),
                review_required=False,
            )
        return UnilogProductClassification(
            product_type_candidate=product_type,
            classpath=None,
            leaf_node=None,
            confidence_bp=8_500 if product_type else 0,
            evidence=(f"description-product-type:{product_type}",) if product_type else (),
            review_required=True,
        )
