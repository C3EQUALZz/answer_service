import traceback
from collections.abc import Iterable

from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair
from answer_service.domain.search.value_objects.ranked_result import RankedResult


def render_exception(exc: BaseException) -> str:
    """Render an exception, including ExceptionGroup leaves, to text.

    ``str(exc)`` on a ``DatureConfigError`` only shows the group header; the
    per-field messages live in nested leaves. Rendering the full traceback lets
    tests assert on those messages.
    """
    return "".join(traceback.format_exception(exc))


def emitted_event_names(collection: EventsCollection) -> list[str]:
    """Drains the collection and names what was in it."""
    return [type(event).__name__ for event in collection.pull_events()]


def external_ids(pairs: Iterable[DesiredPair]) -> list[str]:
    return [pair.external_id.value for pair in pairs]


def ranked_external_ids(results: Iterable[RankedResult]) -> list[str]:
    return [result.external_id.value for result in results]
