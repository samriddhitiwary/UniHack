"""Conservative exact text comparison without semantic similarity."""


def text_comparison_form(value: str) -> str:
    return " ".join(value.split()).casefold()


def text_values_equal(left: str, right: str) -> bool:
    return text_comparison_form(left) == text_comparison_form(right)
