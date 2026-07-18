from dataclasses import dataclass
from typing import override

from answer_service.domain.analytics.errors import NegativeResultsCountError
from answer_service.domain.common.value_object import ValueObject


@dataclass(frozen=True, kw_only=True)
class QueryOutcome(ValueObject):
    """What a query actually produced.

    ``top_score`` is absent exactly when nothing was found, which is the
    condition the whole context exists to surface: a query that returned no
    results is a gap in the catalog, not a failure of the system.
    """

    results_count: int
    top_score: float | None = None

    @property
    def is_unanswered(self) -> bool:
        """Whether the query found nothing at all."""
        return self.results_count == 0

    @override
    def _validate(self) -> None:
        if self.results_count < 0:
            msg = f"Results count cannot be negative, got {self.results_count}."
            raise NegativeResultsCountError(msg)
