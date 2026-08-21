"""Non-hallucination guard for future delivery-field proposals."""

from app.domain.unilog_challenge import EvidenceSourceType, EvidenceStrength, FieldProvenance


def require_supported_provenance(provenance: FieldProvenance) -> None:
    if provenance.value is None:
        return
    if provenance.evidence_strength is EvidenceStrength.UNSUPPORTED:
        raise ValueError("unsupported evidence cannot populate a delivery field")
    if provenance.source_type is EvidenceSourceType.VALIDATED_MODEL_INFERENCE and (
        provenance.confidence_bp < 8_500 or not provenance.review_required
    ):
        raise ValueError("model inference must be high-confidence and reviewable")
