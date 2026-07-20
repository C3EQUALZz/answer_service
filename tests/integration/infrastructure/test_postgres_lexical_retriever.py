"""Keyword retrieval against a real PostgreSQL full-text index.

Everything here depends on the ``english`` text search configuration agreeing
between the generated column and the query. Nothing fails when they drift — the
index simply stops matching — so stemming is asserted directly.
"""

from collections.abc import AsyncIterator

import pytest
from dishka import AsyncContainer, Scope
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.application.common.ports.search import LexicalRetriever
from answer_service.domain.search.value_objects.category_filter import CategoryFilter
from answer_service.domain.search.value_objects.search_criteria import SearchCriteria
from answer_service.domain.search.value_objects.search_query import SearchQuery
from answer_service.domain.search.value_objects.top_k import TopK
from answer_service.infrastructure.adapters.search import PostgresLexicalRetriever
from answer_service.setup.configs.search_config import SearchConfig
from tests.integration.arrange import PairBuilder, PairStorer

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]


def criteria(
    text: str,
    top_k: int = 10,
    category: str | None = None,
) -> SearchCriteria:
    return SearchCriteria(
        query=SearchQuery(content=text),
        top_k=TopK(value=top_k),
        category=CategoryFilter(value=category) if category is not None else None,
    )


@pytest.fixture()
async def _catalog(
    clean_tables: None,
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
) -> None:
    """The three pairs every test here searches over.

    Depends on the truncation rather than leaving it to a mark: the order two
    ``usefixtures`` marks run in is not guaranteed, and seeding before the
    truncate leaves the table empty.
    """
    del clean_tables
    await store_qa_pairs(
        make_pair(
            "q-password",
            question="How do I reset my password?",
            answer="Open settings and choose reset.",
            category="Account",
        ),
        make_pair(
            "q-shipping",
            question="How long does shipping take?",
            answer="Between three and five business days.",
            category="Shipping",
        ),
        make_pair(
            "q-refund",
            question="Can I get a refund?",
            answer="Refunds are issued to the original payment method.",
            category="Billing",
        ),
    )


@pytest.fixture()
async def retriever(
    container: AsyncContainer,
    _catalog: None,
) -> AsyncIterator[LexicalRetriever]:
    """Resolved in its own scope, so it reads through a session that did not write.

    Depends on the catalog rather than leaving it to a mark: the scope opens
    when this fixture runs, and one opened before the seeding commit reads an
    empty table.
    """
    async with container(scope=Scope.REQUEST) as request_container:
        yield await request_container.get(LexicalRetriever)


async def test_a_query_finds_the_pair_that_uses_its_words(
    retriever: LexicalRetriever,
) -> None:
    found = await retriever.retrieve(criteria("reset password"))

    assert [candidate.external_id.value for candidate in found] == ["q-password"]


async def test_words_are_matched_by_stem_not_by_spelling(
    retriever: LexicalRetriever,
) -> None:
    """This is what the ``english`` configuration buys, and what drifts silently."""
    found = await retriever.retrieve(criteria("resetting passwords"))

    assert [candidate.external_id.value for candidate in found] == ["q-password"]


async def test_the_answer_body_is_searched_too(
    retriever: LexicalRetriever,
) -> None:
    found = await retriever.retrieve(criteria("business days"))

    assert [candidate.external_id.value for candidate in found] == ["q-shipping"]


async def test_a_question_match_outranks_an_answer_match(
    retriever: LexicalRetriever,
) -> None:
    """Question text is weighted above answer text for exactly this case."""
    found = await retriever.retrieve(criteria("refund"))

    assert found[0].external_id.value == "q-refund"


async def test_candidates_come_back_ordered_by_relevance(
    retriever: LexicalRetriever,
) -> None:
    """Fusion reads positions, so an unordered list would corrupt the ranking."""
    found = await retriever.retrieve(criteria("refund shipping password"))

    scores = [candidate.score.value for candidate in found]
    assert scores == sorted(scores, reverse=True)


async def test_a_category_filter_excludes_everything_else(
    retriever: LexicalRetriever,
) -> None:
    unfiltered = await retriever.retrieve(criteria("refund shipping"))
    filtered = await retriever.retrieve(
        criteria("refund shipping", category="Shipping"),
    )

    assert {candidate.external_id.value for candidate in unfiltered} == {
        "q-refund",
        "q-shipping",
    }
    assert [candidate.external_id.value for candidate in filtered] == ["q-shipping"]


async def test_top_k_bounds_the_result(retriever: LexicalRetriever) -> None:
    found = await retriever.retrieve(
        criteria("refund shipping password", top_k=1),
    )

    assert len(found) == 1


async def test_matching_nothing_returns_nothing(
    retriever: LexicalRetriever,
) -> None:
    found = await retriever.retrieve(criteria("kubernetes"))

    assert found == []


async def test_punctuation_a_user_typed_does_not_break_the_query(
    retriever: LexicalRetriever,
) -> None:
    """``to_tsquery`` raises on this input; ``websearch_to_tsquery`` does not."""
    found = await retriever.retrieve(criteria("how do I reset my password???"))

    assert [candidate.external_id.value for candidate in found] == ["q-password"]


async def test_a_question_phrased_as_a_sentence_still_matches(
    retriever: LexicalRetriever,
) -> None:
    """Terms are OR-ed, so a pair need not contain every word of the question.

    AND semantics made this retriever silent on exactly the input the service
    exists to answer — no pair holds every word of a natural question.
    """
    found = await retriever.retrieve(criteria("I forgot my password and cannot log in"))

    assert [candidate.external_id.value for candidate in found] == ["q-password"]


async def test_a_pair_covering_more_of_the_query_ranks_higher(
    retriever: LexicalRetriever,
) -> None:
    """OR-ing must not flatten the ranking into 'matched something'."""
    found = await retriever.retrieve(criteria("reset my password settings"))

    assert found[0].external_id.value == "q-password"


async def test_a_query_of_only_stopwords_matches_nothing(
    retriever: LexicalRetriever,
) -> None:
    """Nothing survives normalisation, which must be empty rather than an error."""
    found = await retriever.retrieve(criteria("how do I the a"))

    assert found == []


def retriever_with_floor(
    session: AsyncSession,
    relative_floor: float,
    absolute_floor: float = 0.0,
) -> PostgresLexicalRetriever:
    """Defaults the absolute floor off, so a test names the floor it is about."""
    return PostgresLexicalRetriever(
        session,
        SearchConfig(
            lexical_relative_floor=relative_floor,
            lexical_absolute_floor=absolute_floor,
        ),
    )


@pytest.mark.usefixtures("_catalog")
async def test_a_weak_match_is_kept_or_dropped_by_the_floor_alone(
    container: AsyncContainer,
) -> None:
    """The floor is what lets a query count as unanswered.

    OR-ing terms means almost any query matches something, so without a floor
    every query looks answered and the gap report can never fire. Both floors
    are run against one query so the difference cannot be a missing match.
    """
    query = criteria("refund shipping")

    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        permissive = await retriever_with_floor(session, 0.0).retrieve(query)
        strict = await retriever_with_floor(session, 1.0).retrieve(query)

    assert {candidate.external_id.value for candidate in permissive} == {
        "q-refund",
        "q-shipping",
    }
    assert len(strict) < len(permissive)


@pytest.mark.usefixtures("_catalog")
async def test_the_floor_keeps_a_match_that_covers_the_query(
    container: AsyncContainer,
) -> None:
    """A real match must survive the production floor, or search returns nothing."""
    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        found = await retriever_with_floor(
            session,
            SearchConfig().lexical_relative_floor,
        ).retrieve(criteria("I forgot my password and cannot log in"))

    assert [candidate.external_id.value for candidate in found] == ["q-password"]


@pytest.mark.usefixtures("_catalog")
async def test_the_floor_does_not_depend_on_how_long_the_query_is(
    container: AsyncContainer,
) -> None:
    """The whole reason the floor is relative.

    ``ts_rank_cd`` grows with the number of matched terms, so a fixed threshold
    admits a long question and rejects a short one describing the same need. As
    a fraction of each query's own best match, both behave the same.
    """
    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        retriever = retriever_with_floor(
            session,
            SearchConfig().lexical_relative_floor,
        )
        short = await retriever.retrieve(criteria("password"))
        long = await retriever.retrieve(
            criteria("I forgot my password and cannot log in to my account"),
        )

    assert [candidate.external_id.value for candidate in short] == ["q-password"]
    assert [candidate.external_id.value for candidate in long] == ["q-password"]


@pytest.mark.usefixtures("_catalog")
async def test_a_pair_sharing_one_incidental_word_is_dropped(
    container: AsyncContainer,
) -> None:
    """What the floor exists to remove, stated as a case rather than a number."""
    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        everything = await retriever_with_floor(session, 0.0).retrieve(
            criteria("how long does shipping take"),
        )
        filtered = await retriever_with_floor(
            session,
            SearchConfig().lexical_relative_floor,
        ).retrieve(criteria("how long does shipping take"))

    assert filtered[0].external_id.value == "q-shipping"
    assert len(filtered) <= len(everything)


@pytest.mark.usefixtures("_catalog")
async def test_a_short_query_is_not_punished_for_being_short(
    container: AsyncContainer,
) -> None:
    """The relative floor never empties a set, which is why ranking is its job.

    ``ts_rank_cd`` grows with query length, so ranking against a constant would
    reject every candidate of a perfectly answerable one-word query.
    """
    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        found = await retriever_with_floor(session, 1.0).retrieve(
            criteria("refund"),
        )

    assert found
    assert found[0].external_id.value == "q-refund"


@pytest.mark.usefixtures("_catalog")
async def test_a_query_about_nothing_in_the_catalog_is_refused(
    container: AsyncContainer,
) -> None:
    """What the relative floor structurally cannot do, and the gap report needs.

    Every candidate is compared to the best in its own set, so the best scores
    1.0 against itself and survives every relative setting from 0.0 to 1.0. A
    query that matches only junk is therefore always answered from its best
    piece of junk. Here "days" brushes one word of one answer and nothing else.
    """
    query = criteria("how many days")

    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        relative_only = await retriever_with_floor(session, 1.0).retrieve(query)
        with_absolute = await retriever_with_floor(
            session,
            SearchConfig().lexical_relative_floor,
            SearchConfig().lexical_absolute_floor,
        ).retrieve(query)

    assert relative_only
    assert with_absolute == []


@pytest.mark.usefixtures("_catalog")
async def test_a_real_match_survives_the_absolute_floor(
    container: AsyncContainer,
) -> None:
    """The floor must refuse junk without refusing the catalog's own subjects."""
    async with container(scope=Scope.REQUEST) as scope:
        session = await scope.get(AsyncSession)
        retriever = retriever_with_floor(
            session,
            SearchConfig().lexical_relative_floor,
            SearchConfig().lexical_absolute_floor,
        )
        password = await retriever.retrieve(criteria("I forgot my password"))
        shipping = await retriever.retrieve(criteria("how long does shipping take"))

    assert [candidate.external_id.value for candidate in password] == ["q-password"]
    assert [candidate.external_id.value for candidate in shipping] == ["q-shipping"]
