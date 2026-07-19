from datetime import UTC, datetime

import pytest

from answer_service.domain.indexing.errors import (
    EmptyExternalIdError,
    EmptyQuestionError,
)
from answer_service.infrastructure.mappers import AdaptixSourceRowMapper
from tests.unit.factories.domain_factories import make_source_row


def test_row_columns_land_in_the_matching_value_objects() -> None:
    mapper = AdaptixSourceRowMapper()
    row = make_source_row("faq-1", question="Q?", answer="A.", category="billing")

    pair = mapper.to_desired_pair(row)

    assert pair.external_id.value == "faq-1"
    assert pair.content.question.content == "Q?"
    assert pair.content.answer.content == "A."
    assert pair.content.category.value == "billing"


def test_the_source_timestamp_is_carried_over_under_its_domain_name() -> None:
    """``updated_at`` and ``source_updated_at`` are the same fact, renamed.

    The rename is the one link in this mapping a converter cannot infer, so a
    recipe that lost it would silently leave the planner comparing a default.
    """
    mapper = AdaptixSourceRowMapper()
    moment = datetime(2026, 7, 19, 12, 30, tzinfo=UTC)

    pair = mapper.to_desired_pair(make_source_row("faq-1", updated_at=moment))

    assert pair.source_updated_at == moment


def test_a_blank_external_id_is_refused_while_mapping() -> None:
    """Bad rows must die here, not halfway through applying a sync plan.

    The planner and the catalog both assume every desired pair is valid; a row
    that slipped through would fail after earlier pairs were already written.
    """
    mapper = AdaptixSourceRowMapper()

    with pytest.raises(EmptyExternalIdError):
        mapper.to_desired_pair(make_source_row("   "))


def test_a_blank_question_is_refused_while_mapping() -> None:
    mapper = AdaptixSourceRowMapper()

    with pytest.raises(EmptyQuestionError):
        mapper.to_desired_pair(make_source_row("faq-1", question=" "))


def test_mapping_is_a_pure_function_of_the_row() -> None:
    """The converter is module-level and shared; it must hold no state."""
    mapper = AdaptixSourceRowMapper()
    row = make_source_row("faq-1")

    assert mapper.to_desired_pair(row) == AdaptixSourceRowMapper().to_desired_pair(row)
