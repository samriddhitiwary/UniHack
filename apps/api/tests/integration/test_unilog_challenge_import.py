"""Optional integration against the official locally supplied challenge CSVs."""

import os
from pathlib import Path

import pytest

from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.importers.unilog_challenge import import_unilog_challenge_data


def test_official_challenge_artifacts_when_configured() -> None:
    input_value = os.getenv("UNILOG_CHALLENGE_INPUT_PATH")
    output_value = os.getenv("UNILOG_CHALLENGE_EXPECTED_OUTPUT_PATH")
    if not input_value or not output_value:
        pytest.skip("official challenge artifact paths are not configured")
    imported = import_unilog_challenge_data(Path(input_value), Path(output_value))
    assert imported.statistics.input_rows == 1_000
    assert imported.statistics.input_columns == 6
    assert imported.statistics.expected_output_rows == 2
    assert imported.statistics.expected_output_columns == len(UNILOG_DELIVERY_HEADERS) == 252
    assert imported.statistics.aligned_rows == 2
    assert imported.statistics.ambiguous_rows == 0
    assert imported.statistics.duplicate_input_keys == 1
    assert imported.input_metadata.sha256 == (
        "ed41b50e26c83d0859d563028107fa81a799b5b4b9e3d5743eb846dbd3c7b862"
    )
    assert imported.output_metadata.sha256 == (
        "3304b26f4c3fc3cd5d51b32161cf1900c26e6a7fe238578e53f6f7132df7c580"
    )
