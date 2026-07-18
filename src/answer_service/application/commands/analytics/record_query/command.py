from dataclasses import dataclass

from answer_service.application.common.mediator.markers import Command
from answer_service.domain.analytics.value_objects.query_kind import QueryKind


@dataclass(frozen=True, slots=True)
class RecordQueryCommand(Command[None]):
    """Records one served request for reporting.

    Carries primitives rather than domain value objects: it is dispatched from
    the search and ask endpoints, which measure a duration and count results —
    turning those into validated values is the handler's job.
    """

    text: str
    kind: QueryKind
    results_count: int
    latency_ms: int
    top_score: float | None = None
    category: str | None = None
