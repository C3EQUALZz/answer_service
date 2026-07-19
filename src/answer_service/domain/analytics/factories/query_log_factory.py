import logging
from typing import TYPE_CHECKING, Final, final

from answer_service.domain.analytics.entities.query_log import QueryLog

if TYPE_CHECKING:
    from answer_service.domain.analytics.value_objects.category_label import (
        CategoryLabel,
    )
    from answer_service.domain.analytics.value_objects.latency import Latency
    from answer_service.domain.analytics.value_objects.query_execution import (
        QueryExecution,
    )
    from answer_service.domain.analytics.value_objects.query_kind import QueryKind
    from answer_service.domain.analytics.value_objects.query_log_id import QueryLogId
    from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
    from answer_service.domain.analytics.value_objects.query_text import QueryText


logger: Final[logging.Logger] = logging.getLogger(__name__)


@final
class QueryLogFactory:
    """Domain factory for :class:`QueryLog`.

    Takes no id generator: a served query already has an identity — the
    ``request_id`` minted for it at the entry point and handed back to the
    caller — so the journal records under that same id rather than inventing a
    second one the caller could never correlate against.

    Takes no events collection either: the entity emits no events, so there is
    nothing for a request to collect.
    """

    def create(  # ruff:ignore[too-many-arguments]
        self,
        *,
        query_log_id: QueryLogId,
        text: QueryText,
        kind: QueryKind,
        outcome: QueryOutcome,
        latency: Latency,
        execution: QueryExecution,
        category: CategoryLabel | None = None,
    ) -> QueryLog:
        log = QueryLog(
            id=query_log_id,
            text=text,
            kind=kind,
            outcome=outcome,
            latency=latency,
            execution=execution,
            category=category,
        )
        logger.debug(
            "query_log_factory: created %s for a %s query, %s with %d result(s)",
            log.id,
            kind.value,
            execution.status.value,
            outcome.results_count,
        )
        return log
