"""Answering a question from the catalog.

The dangerous failure here is not an error, it is a fluent answer with nothing
behind it: a chat model handed an empty context answers from its training
instead, and an invented refund policy delivered in the operator's voice reads
exactly like a real one. So most of what is asserted below is about *when the
model is not called*.
"""

import pytest

from answer_service.application.queries.conversation.ask_question.handler import (
    AskQuestionHandler,
)
from answer_service.application.queries.conversation.ask_question.query import (
    AskQuestionQuery,
)
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.search.value_objects.score import Score
from answer_service.domain.search.value_objects.scored_candidate import ScoredCandidate
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from tests.unit.factories.domain_factories import make_qa_content, make_qa_pair
from tests.unit.stubs.gateways import InMemoryQACatalog
from tests.unit.stubs.infrastructure import (
    StubAnswerGenerator,
    StubDenseRetriever,
    StubLexicalRetriever,
)


def make_query(text: str = "how do I reset my password") -> AskQuestionQuery:
    return AskQuestionQuery(
        criteria=SearchCriteria(
            query=SearchQuery(content=text),
            top_k=TopK(value=3),
        ),
    )


def candidate(external_id: str, score: float) -> ScoredCandidate:
    return ScoredCandidate(
        external_id=ExternalId(value=external_id),
        score=Score(value=score),
    )


@pytest.fixture(autouse=True)
async def _seeded_catalog(
    catalog: InMemoryQACatalog,
    events_collection: EventsCollection,
) -> None:
    for external_id in ("q-1", "q-2"):
        await catalog.add(
            make_qa_pair(
                external_id,
                events_collection,
                make_qa_content(
                    question=f"Question {external_id}?",
                    answer=f"Answer {external_id}.",
                    category="account",
                ),
            ),
        )


async def test_an_answer_is_written_from_what_was_retrieved(
    ask_question_handler: AskQuestionHandler,
    dense_retriever: StubDenseRetriever,
    answer_generator: StubAnswerGenerator,
) -> None:
    dense_retriever.candidates = [candidate("q-1", 0.9)]

    response = await ask_question_handler.handle(make_query())

    assert response.is_answered
    assert response.answer is not None
    assert response.answer.text.content == answer_generator.text

    question, grounding = answer_generator.calls[0]
    assert question == "how do I reset my password"
    assert [pair.external_id for pair in grounding] == ["q-1"]


async def test_the_answer_cites_every_pair_it_was_grounded_in(
    ask_question_handler: AskQuestionHandler,
    dense_retriever: StubDenseRetriever,
    lexical_retriever: StubLexicalRetriever,
) -> None:
    """Sources are what make the answer checkable; an uncited one is unverifiable."""
    dense_retriever.candidates = [candidate("q-1", 0.9)]
    lexical_retriever.candidates = [candidate("q-2", 0.5)]

    response = await ask_question_handler.handle(make_query())

    assert response.answer is not None
    assert {source.value for source in response.answer.sources} == {"q-1", "q-2"}


async def test_nothing_retrieved_means_no_answer_and_no_model_call(
    ask_question_handler: AskQuestionHandler,
    answer_generator: StubAnswerGenerator,
) -> None:
    """The safeguard: an empty context must never reach the model."""
    response = await ask_question_handler.handle(make_query("what is the weather?"))

    assert not response.is_answered
    assert response.answer is None
    assert response.grounding == ()
    assert answer_generator.calls == []


async def test_an_unanswerable_question_is_returned_rather_than_raised(
    ask_question_handler: AskQuestionHandler,
) -> None:
    """It is the entry the gap report is built from, so it has to be a result."""
    response = await ask_question_handler.handle(make_query("what is the weather?"))

    assert response.results_count == 0
    assert response.top_score is None


async def test_the_grounding_is_reported_alongside_the_answer(
    ask_question_handler: AskQuestionHandler,
    dense_retriever: StubDenseRetriever,
) -> None:
    """A caller showing sources needs their text, not just their identities."""
    dense_retriever.candidates = [candidate("q-1", 0.9)]

    response = await ask_question_handler.handle(make_query())

    assert [hit.pair.external_id for hit in response.grounding] == ["q-1"]
    assert response.grounding[0].pair.question == "Question q-1?"
    assert response.results_count == 1
    assert response.top_score is not None


async def test_a_pair_the_catalog_no_longer_holds_is_not_cited(
    ask_question_handler: AskQuestionHandler,
    dense_retriever: StubDenseRetriever,
    answer_generator: StubAnswerGenerator,
) -> None:
    """The dense index lags the catalog, so it ranks pairs that are already gone."""
    dense_retriever.candidates = [candidate("q-deleted", 0.99), candidate("q-1", 0.5)]

    response = await ask_question_handler.handle(make_query())

    assert response.answer is not None
    assert {source.value for source in response.answer.sources} == {"q-1"}
    _, grounding = answer_generator.calls[0]
    assert [pair.external_id for pair in grounding] == ["q-1"]
