from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import final

from answer_service.domain.analytics.value_objects.category_label import CategoryLabel
from answer_service.domain.analytics.value_objects.latency import Latency
from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from answer_service.domain.analytics.value_objects.query_log_id import QueryLogId
from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
from answer_service.domain.analytics.value_objects.query_text import QueryText
from answer_service.domain.common.entity import Entity


@final
@dataclass(eq=False, kw_only=True)
class QueryLog(Entity[QueryLogId]):
    """One recorded request: what was asked, and what came back.

    An ``Entity`` rather than an ``Aggregate`` on purpose. It emits no domain
    events — nothing downstream reacts to a query having been logged — and an
    aggregate would only add an events collection nobody drains.

    Built straight through its dataclass constructor — with no events to raise,
    a named constructor would only restate the field list. Construction goes
    through ``QueryLogFactory``, which supplies the identity.

    Immutable after creation in practice: a log entry records something that
    already happened, so there is no operation that could change it. Statistics
    are never stored here; they are computed from these entries on read, which
    keeps a single fact from having to be kept consistent in two places.
    """

    text: QueryText
    kind: QueryKind
    outcome: QueryOutcome
    latency: Latency
    category: CategoryLabel | None = field(default=None)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_unanswered(self) -> bool:
        """Whether this request found nothing — a gap worth reporting."""
        return self.outcome.is_unanswered
