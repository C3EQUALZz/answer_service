from answer_service.domain.analytics.value_objects.query_kind import QueryKind
from tests.unit.factories.domain_factories import make_query_log


def test_a_log_entry_keeps_what_it_was_given() -> None:
    log = make_query_log("how do I export data?", results_count=4, latency_ms=120)

    assert log.text.content == "how do I export data?"
    assert log.outcome.results_count == 4
    assert log.latency.milliseconds == 120
    assert log.kind is QueryKind.SEARCH


def test_a_log_entry_exposes_the_gap_flag_of_its_outcome() -> None:
    assert make_query_log(results_count=0).is_unanswered
    assert not make_query_log(results_count=1).is_unanswered


def test_a_category_is_optional() -> None:
    """A search without a filter is the common case."""
    assert make_query_log().category is None
    assert make_query_log(category="billing").category is not None


def test_ask_and_search_are_recorded_apart() -> None:
    """Statistics report the two entry points separately."""
    assert make_query_log(kind=QueryKind.ASK).kind is QueryKind.ASK
    assert QueryKind.ASK != QueryKind.SEARCH
