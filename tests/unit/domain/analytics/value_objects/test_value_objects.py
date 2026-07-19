from datetime import UTC, datetime, timedelta

import pytest

from answer_service.domain.analytics.errors import (
    EmptyCategoryLabelError,
    EmptyErrorCodeError,
    EmptyQueryTextError,
    InconsistentQueryExecutionError,
    InvalidPeriodError,
    NegativeLatencyError,
    NegativeResultsCountError,
    QueryTextTooLongError,
)
from answer_service.domain.analytics.value_objects.category_label import CategoryLabel
from answer_service.domain.analytics.value_objects.error_code import ErrorCode
from answer_service.domain.analytics.value_objects.latency import Latency
from answer_service.domain.analytics.value_objects.period import Period
from answer_service.domain.analytics.value_objects.query_execution import QueryExecution
from answer_service.domain.analytics.value_objects.query_outcome import QueryOutcome
from answer_service.domain.analytics.value_objects.query_status import QueryStatus
from answer_service.domain.analytics.value_objects.query_text import (
    MAX_QUERY_TEXT_LENGTH,
    QueryText,
)

NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def test_logged_text_must_have_content() -> None:
    with pytest.raises(EmptyQueryTextError):
        QueryText(content=" ")


def test_logged_text_has_a_ceiling() -> None:
    with pytest.raises(QueryTextTooLongError):
        QueryText(content="q" * (MAX_QUERY_TEXT_LENGTH + 1))


def test_a_category_label_must_name_something() -> None:
    with pytest.raises(EmptyCategoryLabelError):
        CategoryLabel(value="")


def test_latency_cannot_be_negative() -> None:
    assert Latency(milliseconds=0).milliseconds == 0

    with pytest.raises(NegativeLatencyError):
        Latency(milliseconds=-1)


def test_an_outcome_with_no_results_is_unanswered() -> None:
    """The gap report is built entirely on this flag."""
    assert QueryOutcome(results_count=0).is_unanswered
    assert not QueryOutcome(results_count=1, top_score=0.4).is_unanswered


def test_a_negative_result_count_is_rejected() -> None:
    with pytest.raises(NegativeResultsCountError):
        QueryOutcome(results_count=-1)


def test_an_error_code_must_name_something() -> None:
    with pytest.raises(EmptyErrorCodeError):
        ErrorCode(value="  ")


def test_a_succeeded_execution_carries_no_error_code() -> None:
    execution = QueryExecution.succeeded()

    assert execution.status is QueryStatus.SUCCEEDED
    assert execution.error_code is None
    assert not execution.is_failed


def test_a_failed_execution_records_its_code() -> None:
    execution = QueryExecution.failed(ErrorCode(value="SearchIndexError"))

    assert execution.status is QueryStatus.FAILED
    assert execution.is_failed
    assert execution.error_code == ErrorCode(value="SearchIndexError")


def test_a_failure_without_a_code_is_rejected() -> None:
    """A failure the report cannot label is one it cannot group or act on."""
    with pytest.raises(InconsistentQueryExecutionError):
        QueryExecution(QueryStatus.FAILED)


def test_a_success_carrying_a_code_is_rejected() -> None:
    """A code on a success describes nothing, so it must not be storable."""
    with pytest.raises(InconsistentQueryExecutionError):
        QueryExecution(QueryStatus.SUCCEEDED, ErrorCode(value="SearchIndexError"))


def test_a_period_cannot_end_before_it_starts() -> None:
    earlier = NOW - timedelta(seconds=1)

    with pytest.raises(InvalidPeriodError):
        Period(start=NOW, end=earlier)


def test_an_empty_period_is_allowed() -> None:
    """An instant window contains nothing, which is an answer, not an error."""
    period = Period(start=NOW, end=NOW)

    assert not period.contains(NOW)


def test_a_period_includes_its_start_and_excludes_its_end() -> None:
    """Half-open, so consecutive periods tile without counting a boundary twice."""
    period = Period(start=NOW, end=NOW + timedelta(days=1))

    assert period.contains(NOW)
    assert period.contains(NOW + timedelta(hours=23, minutes=59))
    assert not period.contains(period.end)
    assert not period.contains(NOW - timedelta(seconds=1))


def test_last_days_ends_at_the_given_moment() -> None:
    period = Period.last_days(7, now=NOW)

    assert period.end == NOW
    assert period.start == NOW - timedelta(days=7)
    assert period.contains(NOW - timedelta(days=3))


def test_consecutive_periods_do_not_overlap() -> None:
    earlier = Period(start=NOW - timedelta(days=1), end=NOW)
    later = Period(start=NOW, end=NOW + timedelta(days=1))

    assert not earlier.contains(NOW)
    assert later.contains(NOW)
