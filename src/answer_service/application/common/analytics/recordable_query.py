from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from answer_service.application.common.mediator.markers import Query
from answer_service.domain.analytics.value_objects.query_kind import QueryKind


@runtime_checkable
class ServedQuery(Protocol):
    """What a recordable query's response must say about how it went.

    Deliberately the two numbers the gap report is built from and nothing else:
    a query that found nothing is the entry the report exists to surface, so
    "how many" and "how well" are the whole contract.
    """

    @property
    def results_count(self) -> int: ...

    @property
    def top_score(self) -> float | None: ...


@dataclass(frozen=True)
class RecordableQuery[TResponse: ServedQuery](Query[TResponse], ABC):
    """A query whose serving is written to the analytics journal.

    The recording pipeline is registered against this marker rather than against
    each query, so a query added later is journalled by inheriting from this
    instead of by someone remembering to add a call at the route. That is the
    same bargain the transaction pipeline makes with ``Command``: coverage by
    type, not by discipline.

    The three members below are what a journal entry needs that the response
    cannot supply — they describe the request, not its outcome.

    ``request_id`` is minted here, at the request, rather than by the journal:
    it is the correlation id the search and ask endpoints hand back, and it can
    only be in the response *and* be the row's identity if it exists before the
    handler runs. Keyword-only so a subclass can keep its own required fields
    positional.
    """

    request_id: UUID = field(default_factory=uuid4, kw_only=True)

    @property
    @abstractmethod
    def journalled_text(self) -> str:
        """The words the user typed, as they will appear in the report."""

    @property
    @abstractmethod
    def journalled_kind(self) -> QueryKind:
        """Which entry point served this."""

    @property
    def journalled_category(self) -> str | None:
        """The category filter in force, if the caller set one."""
        return None
