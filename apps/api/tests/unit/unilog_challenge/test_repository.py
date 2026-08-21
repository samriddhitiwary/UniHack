"""Direct-key challenge repository tests."""

import csv
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.domain.unilog_challenge.delivery_schema import UNILOG_DELIVERY_HEADERS
from app.importers.unilog_challenge import import_unilog_challenge_data
from app.repositories.in_memory_unilog_challenge import InMemoryUnilogChallengeRepository


def _import(tmp_path: Path):  # type: ignore[no-untyped-def]
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    with input_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["Mfg_Part_Num", "Part_Desc", "E1_Brand", "Unilog_Brand", "DIB_Brand", "Part_Manuf"]
        )
        writer.writerow(["P1", "Item one", "Brand®", "", "", "Maker LLC (M1)"])
        writer.writerow(["P1", "Item duplicate", "", "", "", "Maker LLC (M1)"])
        writer.writerow(["P2", "Item two", "", "", "", "Other Ltd"])
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=UNILOG_DELIVERY_HEADERS)
        writer.writeheader()
        writer.writerow({"Mfg_Part_Num": "P2", "MANUFACTURER_NAME": "Other Ltd"})
    return import_unilog_challenge_data(
        input_path, output_path, imported_at=datetime(2026, 8, 21, tzinfo=UTC)
    )


def test_repository_rebuilds_direct_indexes_and_bounds_results(tmp_path: Path) -> None:
    imported = _import(tmp_path)
    repository = InMemoryUnilogChallengeRepository()
    assert repository.get_metadata() is None
    repository.replace(imported)
    assert repository.import_id == imported.import_id
    assert repository.get_input_by_id(imported.input_rows[2].row_id) == imported.input_rows[2]
    assert len(repository.get_inputs_by_part_number("P1")) == 2
    assert len(repository.get_inputs_by_part_number("P1", limit=1)) == 1
    assert repository.get_ground_truth_by_part_number("P2")[0].mfg_part_num == "P2"
    assert repository.get_observed_vocabulary() == imported.observed_vocabulary
    assert repository.get_metadata() == (imported.input_metadata, imported.output_metadata)


@pytest.mark.parametrize("limit", [0, 101, True])
def test_repository_rejects_unbounded_limits(tmp_path: Path, limit: int) -> None:
    repository = InMemoryUnilogChallengeRepository()
    repository.replace(_import(tmp_path))
    with pytest.raises(ValueError, match="between 1 and 100"):
        repository.get_inputs_by_part_number("P1", limit=limit)
