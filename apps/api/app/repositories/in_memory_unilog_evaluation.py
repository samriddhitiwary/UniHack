"""Process-local indexed evaluation repository for explicit hackathon runs."""

from app.domain.unilog_evaluation import UnilogEvaluationResult


class InMemoryUnilogEvaluationRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, UnilogEvaluationResult] = {}
        self._latest_id: str | None = None

    def save(self, result: UnilogEvaluationResult) -> None:
        self._by_id[result.evaluation_id] = result
        self._latest_id = result.evaluation_id

    def get(self, evaluation_id: str) -> UnilogEvaluationResult | None:
        return self._by_id.get(evaluation_id)

    def latest(self) -> UnilogEvaluationResult | None:
        return None if self._latest_id is None else self._by_id[self._latest_id]
