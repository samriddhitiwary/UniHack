"""Indexed repository contract for challenge data kept outside Product storage."""

from typing import Protocol

from app.domain.unilog_challenge import (
    DatasetMetadata,
    ObservedVocabulary,
    UnilogChallengeImport,
    UnilogChallengeInputRow,
    UnilogGroundTruthRecord,
)


class UnilogChallengeRepository(Protocol):
    def replace(self, imported: UnilogChallengeImport) -> None: ...

    def get_input_by_id(self, row_id: str) -> UnilogChallengeInputRow | None: ...

    def get_inputs_by_part_number(
        self, mfg_part_num: str, *, limit: int = 10
    ) -> tuple[UnilogChallengeInputRow, ...]: ...

    def get_ground_truth_by_part_number(
        self, mfg_part_num: str, *, limit: int = 10
    ) -> tuple[UnilogGroundTruthRecord, ...]: ...

    def get_observed_vocabulary(self) -> ObservedVocabulary | None: ...

    def get_metadata(self) -> tuple[DatasetMetadata, DatasetMetadata] | None: ...
