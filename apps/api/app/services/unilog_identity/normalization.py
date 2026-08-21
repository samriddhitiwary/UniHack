"""Conservative normalization shared by identity evidence indexes."""

import re


def normalize_identity(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def compact_identity(value: str) -> str:
    return normalize_identity(value).replace(" ", "")


def mpn_prefix(value: str) -> str | None:
    head = value.split("-", 1)[0]
    if "-" not in value:
        match = re.match(r"[A-Za-z]+", value)
        head = match.group() if match else ""
    normalized = re.sub(r"[^A-Za-z0-9]", "", head).upper()
    return (
        normalized if len(normalized) >= 2 and any(char.isalpha() for char in normalized) else None
    )


def leading_phrase(value: str) -> tuple[str, tuple[int, int]] | None:
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9&.+-]*)", value)
    if match is None:
        return None
    raw = match.group(1).strip("-+.")
    normalized = normalize_identity(raw)
    if not normalized or not any(char.isalpha() for char in normalized):
        return None
    return raw, (match.start(1), match.start(1) + len(raw))
