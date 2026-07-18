import pytest

from answer_service.domain.indexing.errors import (
    AnswerTooLongError,
    EmptyAnswerError,
    EmptyCategoryError,
    EmptyExternalIdError,
    EmptyFailureCodeError,
    EmptyQuestionError,
    EmptySourceReferenceError,
    InvalidContentHashError,
    NegativeSyncCountError,
    QuestionTooLongError,
)
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.content_hash import ContentHash
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.failure_info import FailureInfo
from answer_service.domain.indexing.value_objects.qa_content import QAContent
from answer_service.domain.indexing.value_objects.question import Question
from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats
from answer_service.domain.indexing.value_objects.task_status import IndexingTaskStatus


@pytest.mark.parametrize("blank", ("", "   ", "\t\n"))
def test_blank_strings_are_rejected_everywhere(blank: str) -> None:
    """Whitespace is not content — every text value object must agree."""
    with pytest.raises(EmptyExternalIdError):
        ExternalId(value=blank)
    with pytest.raises(EmptyQuestionError):
        Question(content=blank)
    with pytest.raises(EmptyAnswerError):
        Answer(content=blank)
    with pytest.raises(EmptyCategoryError):
        Category(value=blank)
    with pytest.raises(EmptySourceReferenceError):
        SourceReference(value=blank)


def test_overlong_text_is_rejected() -> None:
    from answer_service.domain.indexing.value_objects.answer import MAX_ANSWER_LENGTH
    from answer_service.domain.indexing.value_objects.question import (
        MAX_QUESTION_LENGTH,
    )

    with pytest.raises(QuestionTooLongError):
        Question(content="q" * (MAX_QUESTION_LENGTH + 1))
    with pytest.raises(AnswerTooLongError):
        Answer(content="a" * (MAX_ANSWER_LENGTH + 1))


def test_value_objects_compare_by_value() -> None:
    assert ExternalId(value="q-1") == ExternalId(value="q-1")
    assert ExternalId(value="q-1") != ExternalId(value="q-2")


def make_content(
    question: str = "Q?",
    answer: str = "A.",
    category: str = "c",
) -> QAContent:
    return QAContent(
        question=Question(content=question),
        answer=Answer(content=answer),
        category=Category(value=category),
    )


def test_the_same_content_always_hashes_the_same() -> None:
    """Sync idempotency rests entirely on this."""
    assert make_content().fingerprint == make_content().fingerprint


@pytest.mark.parametrize(
    ("question", "answer", "category"),
    (
        ("changed", "A.", "c"),
        ("Q?", "changed", "c"),
        ("Q?", "A.", "changed"),
    ),
)
def test_changing_any_field_changes_the_hash(
    question: str,
    answer: str,
    category: str,
) -> None:
    assert make_content(question, answer, category).fingerprint != (
        make_content().fingerprint
    )


def test_field_boundaries_cannot_be_shifted_between_fields() -> None:
    """Concatenating without a separator would make these two collide.

    ``("ab", "c")`` and ``("a", "bc")`` are different content; a hash that
    cannot tell them apart would silently skip a real update.
    """
    assert make_content("ab", "c").fingerprint != make_content("a", "bc").fingerprint


def test_a_hash_that_is_not_a_sha256_digest_is_rejected() -> None:
    with pytest.raises(InvalidContentHashError):
        ContentHash(value="too-short")


def test_sync_stats_total_is_the_sum() -> None:
    stats = SyncStats(created=1, updated=2, deleted=3, skipped=4)

    assert stats.total == 10
    assert SyncStats.empty().total == 0


@pytest.mark.parametrize(
    "counters",
    (
        {"created": -1, "updated": 0, "deleted": 0, "skipped": 0},
        {"created": 0, "updated": -1, "deleted": 0, "skipped": 0},
        {"created": 0, "updated": 0, "deleted": -1, "skipped": 0},
        {"created": 0, "updated": 0, "deleted": 0, "skipped": -1},
    ),
)
def test_negative_counters_are_rejected(counters: dict[str, int]) -> None:
    with pytest.raises(NegativeSyncCountError):
        SyncStats(**counters)


def test_a_failure_needs_a_code() -> None:
    with pytest.raises(EmptyFailureCodeError):
        FailureInfo(code="  ", message="something went wrong")


def test_a_failure_renders_code_and_message() -> None:
    assert str(FailureInfo(code="Boom", message="bad file")) == "[Boom] bad file"


@pytest.mark.parametrize(
    ("status", "terminal"),
    (
        (IndexingTaskStatus.QUEUED, False),
        (IndexingTaskStatus.RUNNING, False),
        (IndexingTaskStatus.SUCCEEDED, True),
        (IndexingTaskStatus.FAILED, True),
    ),
)
def test_only_finished_states_are_terminal(
    status: IndexingTaskStatus,
    *,
    terminal: bool,
) -> None:
    assert status.is_terminal is terminal
