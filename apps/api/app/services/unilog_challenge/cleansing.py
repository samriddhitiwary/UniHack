"""Conservative challenge-value cleansing."""

_PLACEHOLDERS = frozenset(
    value.casefold()
    for value in (
        "-- Unbranded --",
        "-- No Unilog Brand --",
        "-- No DIB Brand --",
    )
)


def clean_challenge_value(value: str | None) -> str | None:
    """Remove only blanks and observed organizer placeholder values."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.casefold() in _PLACEHOLDERS:
        return None
    return cleaned


def is_challenge_placeholder(value: str | None) -> bool:
    return value is not None and value.strip().casefold() in _PLACEHOLDERS
