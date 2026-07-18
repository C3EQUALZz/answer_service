"""The QAPair mapping against a real database, through its ports.

``QAContent`` is stored as a composite over three columns — assembled
positionally, and failing silently rather than loudly — so it is checked end to
end here.
"""

from uuid import uuid4

import pytest
from dishka import AsyncContainer, FromDishka, Scope

from answer_service.application.common.ports.gateways import (
    QACatalogCommandGateway,
    QACatalogQueryGateway,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.integration.inject import inject
from tests.integration.persistence.conftest import PairBuilder, PairStorer
from tests.unit.factories.domain_factories import SOURCE_UPDATED_AT, make_qa_content

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
    pytest.mark.usefixtures("clean_tables"),
]


@inject
async def test_a_pair_round_trips_through_the_composite(
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    gateway: FromDishka[QACatalogCommandGateway],
) -> None:
    await store_qa_pairs(
        make_pair("q-1", question="How?", answer="Like this.", category="howto"),
    )

    loaded = await gateway.read_by_id(ExternalId(value="q-1"))

    assert loaded is not None
    assert loaded.id == ExternalId(value="q-1")
    assert loaded.content.question.content == "How?"
    assert loaded.content.answer.content == "Like this."
    assert loaded.content.category.value == "howto"


@inject
async def test_the_fingerprint_survives_a_round_trip(
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    gateway: FromDishka[QACatalogCommandGateway],
) -> None:
    """Sync correctness depends on stored content hashing to the same value."""
    pair = make_pair("q-1")
    expected = pair.content.fingerprint
    await store_qa_pairs(pair)

    loaded = await gateway.read_by_id(ExternalId(value="q-1"))

    assert loaded is not None
    assert loaded.content.fingerprint == expected
    assert loaded.matches(expected)


async def test_a_loaded_pair_can_be_mutated_and_saved(
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    container: AsyncContainer,
) -> None:
    """A loaded aggregate needs its events collection injected, or this raises."""
    await store_qa_pairs(make_pair("q-1", answer="Old answer."))

    async with container(scope=Scope.REQUEST) as writer_scope:
        gateway = await writer_scope.get(QACatalogCommandGateway)
        loaded = await gateway.read_by_id(ExternalId(value="q-1"))
        assert loaded is not None
        changed = loaded.update_content(
            content=make_qa_content(answer="New answer."),
            source_updated_at=SOURCE_UPDATED_AT,
        )
        await (await writer_scope.get(TransactionManager)).commit()

    assert changed
    async with container(scope=Scope.REQUEST) as reader_scope:
        reloaded = await (await reader_scope.get(QACatalogCommandGateway)).read_by_id(
            ExternalId(value="q-1")
        )

    assert reloaded is not None
    assert reloaded.content.answer.content == "New answer."


async def test_deleting_removes_the_pair(
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    container: AsyncContainer,
) -> None:
    await store_qa_pairs(make_pair("q-1"))

    async with container(scope=Scope.REQUEST) as writer_scope:
        gateway = await writer_scope.get(QACatalogCommandGateway)
        await gateway.delete_by_id(ExternalId(value="q-1"))
        await (await writer_scope.get(TransactionManager)).commit()

    async with container(scope=Scope.REQUEST) as reader_scope:
        reloaded = await (await reader_scope.get(QACatalogCommandGateway)).read_by_id(
            ExternalId(value="q-1")
        )

    assert reloaded is None


@inject
async def test_the_manifest_hashes_match_the_stored_content(
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    query_gateway: FromDishka[QACatalogQueryGateway],
) -> None:
    """The planner diffs against this; a wrong hash re-syncs the whole catalog."""
    first = make_pair("q-1", answer="First answer.")
    second = make_pair("q-2", answer="Second answer.")
    await store_qa_pairs(first, second)

    manifest = await query_gateway.read_fingerprints()

    assert manifest == {
        ExternalId(value="q-1"): first.content.fingerprint,
        ExternalId(value="q-2"): second.content.fingerprint,
    }


@inject
async def test_an_empty_catalog_has_an_empty_manifest(
    query_gateway: FromDishka[QACatalogQueryGateway],
) -> None:
    assert await query_gateway.read_fingerprints() == {}


@inject
async def test_statistics_are_counted_by_the_database(
    make_pair: PairBuilder,
    store_qa_pairs: PairStorer,
    query_gateway: FromDishka[QACatalogQueryGateway],
) -> None:
    await store_qa_pairs(
        make_pair("q-1", category="billing"),
        make_pair("q-2", category="billing"),
        make_pair("q-3", category="account"),
    )

    statistics = await query_gateway.read_statistics()

    assert statistics.total_pairs == 3
    assert statistics.pairs_per_category == {"billing": 2, "account": 1}
    assert statistics.category_count == 2


@inject
async def test_statistics_of_an_empty_catalog_are_zero(
    query_gateway: FromDishka[QACatalogQueryGateway],
) -> None:
    statistics = await query_gateway.read_statistics()

    assert statistics.total_pairs == 0
    assert statistics.pairs_per_category == {}


@inject
async def test_an_unknown_pair_is_absent_not_an_error(
    gateway: FromDishka[QACatalogCommandGateway],
) -> None:
    assert await gateway.read_by_id(ExternalId(value=str(uuid4()))) is None
