from typing import TYPE_CHECKING, Final, final

from answer_service.domain.analytics.entities.query_log import QueryLog
from answer_service.domain.analytics.ports.id_generator import QueryLogIdGenerator

if TYPE_CHECKING:
    from answer_service.domain.analytics.value_objects.category_label import (
        CategoryLabel,
    )
    from answer_service.domain.analytics.value_objects.latency import Latency
    from answer_service.domain.analytics.value_objects.query_kind import QueryKind
    from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
    from answer_service.domain.analytics.value_objects.query_text import QueryText


@final
class QueryLogFactory:
    """Domain factory for :class:`QueryLog`.

    Takes no events collection: the entity emits no events, so there is nothing
    for a request to collect.
    """

    def __init__(self, query_log_id_generator: QueryLogIdGenerator) -> None:
        self._query_log_id_generator: Final[QueryLogIdGenerator] = query_log_id_generator

    def create(
        self,
        *,
        text: QueryText,
        kind: QueryKind,
        outcome: QueryOutcome,
        latency: Latency,
        category: CategoryLabel | None = None,
    ) -> QueryLog:
        return QueryLog(
            id=self._query_log_id_generator(),
            text=text,
            kind=kind,
            outcome=outcome,
            latency=latency,
            category=category,
        )
