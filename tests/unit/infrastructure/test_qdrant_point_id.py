from uuid import UUID

from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.infrastructure.adapters.search.qdrant_search_index_writer import (
    point_id_of,
)


def test_a_point_id_is_a_uuid() -> None:
    """Qdrant accepts only UUIDs or integers — an external id is neither."""
    assert UUID(point_id_of(ExternalId(value="faq-42")))


def test_the_same_external_id_always_maps_to_the_same_point() -> None:
    """This is what makes upsert idempotent instead of duplicating on re-index."""
    first = point_id_of(ExternalId(value="faq-42"))
    second = point_id_of(ExternalId(value="faq-42"))

    assert first == second


def test_different_external_ids_map_to_different_points() -> None:
    assert point_id_of(ExternalId(value="faq-1")) != point_id_of(
        ExternalId(value="faq-2"),
    )


def test_ids_that_differ_only_in_case_are_distinct() -> None:
    """External ids come from customer files and are treated as opaque."""
    assert point_id_of(ExternalId(value="FAQ-1")) != point_id_of(
        ExternalId(value="faq-1"),
    )


def test_awkward_external_ids_still_produce_valid_points() -> None:
    """The id is whatever the customer put in the column."""
    for value in ("with space", "non-latin identifier", "slash/and:colon", "42"):
        assert UUID(point_id_of(ExternalId(value=value)))


def test_the_mapping_is_stable_across_processes() -> None:
    """A hash seeded per process would silently orphan every indexed point."""
    assert point_id_of(ExternalId(value="faq-42")) == (
        "6fcb60c7-a6d5-56a7-8b5b-fefaa3ae4ff7"
    )
