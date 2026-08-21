"""Separate persistence boundary for immutable Unilog evaluation results."""

from typing import Protocol

from app.domain.unilog_evaluation import UnilogEvaluationResult


class UnilogEvaluationRepository(Protocol):
    def save(self, result: UnilogEvaluationResult) -> None: ...

    def get(self, evaluation_id: str) -> UnilogEvaluationResult | None: ...

    def latest(self) -> UnilogEvaluationResult | None: ...
