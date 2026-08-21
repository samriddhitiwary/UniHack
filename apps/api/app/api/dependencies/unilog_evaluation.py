"""Process-local evaluation dependencies; creation remains an explicit API action."""

from app.repositories.in_memory_unilog_evaluation import (
    InMemoryUnilogEvaluationRepository,
)
from app.repositories.unilog_evaluation import UnilogEvaluationRepository
from app.services.unilog_evaluation.evaluation_service import UnilogEvaluationService

_repository = InMemoryUnilogEvaluationRepository()


def get_unilog_evaluation_repository() -> UnilogEvaluationRepository:
    return _repository


def get_unilog_evaluation_service() -> UnilogEvaluationService:
    return UnilogEvaluationService(_repository)
