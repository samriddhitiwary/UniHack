"""Deterministic direct-key challenge repository for batch/import use."""

from collections import defaultdict

from app.domain.unilog_challenge import (
    DatasetMetadata,
    ObservedVocabulary,
    UnilogChallengeImport,
    UnilogChallengeInputRow,
    UnilogGroundTruthRecord,
)


class InMemoryUnilogChallengeRepository:
    """Immutable-after-rebuild indexes; lookup methods never scan the datasets."""

    def __init__(self) -> None:
        self._by_id: dict[str, UnilogChallengeInputRow] = {}
        self._inputs_by_part: dict[str, tuple[UnilogChallengeInputRow, ...]] = {}
        self._truth_by_part: dict[str, tuple[UnilogGroundTruthRecord, ...]] = {}
        self._vocabulary: ObservedVocabulary | None = None
        self._metadata: tuple[DatasetMetadata, DatasetMetadata] | None = None
        self.import_id: str | None = None

    def replace(self, imported: UnilogChallengeImport) -> None:
        inputs_by_part: dict[str, list[UnilogChallengeInputRow]] = defaultdict(list)
        truth_by_part: dict[str, list[UnilogGroundTruthRecord]] = defaultdict(list)
        by_id = {row.row_id: row for row in imported.input_rows}
        for input_row in imported.input_rows:
            inputs_by_part[input_row.mfg_part_num].append(input_row)
        for truth_row in imported.ground_truth_rows:
            truth_by_part[truth_row.mfg_part_num].append(truth_row)
        self._by_id = by_id
        self._inputs_by_part = {key: tuple(value) for key, value in inputs_by_part.items()}
        self._truth_by_part = {key: tuple(value) for key, value in truth_by_part.items()}
        self._vocabulary = imported.observed_vocabulary
        self._metadata = (imported.input_metadata, imported.output_metadata)
        self.import_id = imported.import_id

    def get_input_by_id(self, row_id: str) -> UnilogChallengeInputRow | None:
        return self._by_id.get(row_id)

    def get_inputs_by_part_number(
        self, mfg_part_num: str, *, limit: int = 10
    ) -> tuple[UnilogChallengeInputRow, ...]:
        _validate_limit(limit)
        return self._inputs_by_part.get(mfg_part_num, ())[:limit]

    def get_ground_truth_by_part_number(
        self, mfg_part_num: str, *, limit: int = 10
    ) -> tuple[UnilogGroundTruthRecord, ...]:
        _validate_limit(limit)
        return self._truth_by_part.get(mfg_part_num, ())[:limit]

    def get_observed_vocabulary(self) -> ObservedVocabulary | None:
        return self._vocabulary

    def get_metadata(self) -> tuple[DatasetMetadata, DatasetMetadata] | None:
        return self._metadata


def _validate_limit(limit: int) -> None:
    if isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("lookup limit must be between 1 and 100")
