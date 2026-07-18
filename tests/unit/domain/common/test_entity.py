from datetime import UTC, datetime, timedelta

import pytest

from answer_service.domain.common.entity import Entity
from answer_service.domain.common.error import DomainError, InconsistentTimeError


class SampleEntity(Entity[str]):
    pass


def test_two_entities_with_the_same_id_are_equal() -> None:
    """Identity, not attribute equality — that is what makes it an entity."""
    assert SampleEntity(id="a") == SampleEntity(id="a")
    assert SampleEntity(id="a") != SampleEntity(id="b")


def test_entities_hash_by_id() -> None:
    assert len({SampleEntity(id="a"), SampleEntity(id="a")}) == 1


def test_comparing_with_a_non_entity_is_not_an_error() -> None:
    assert SampleEntity(id="a") != "a"


def test_the_id_cannot_be_changed_once_set() -> None:
    """An aggregate that changes identity silently corrupts every reference."""
    entity = SampleEntity(id="a")

    with pytest.raises(DomainError, match="Changing entity ID"):
        entity.id = "b"


def test_other_attributes_stay_mutable() -> None:
    entity = SampleEntity(id="a")
    moment = datetime.now(UTC)

    entity.updated_at = moment

    assert entity.updated_at == moment


def test_updated_at_cannot_precede_created_at() -> None:
    created = datetime.now(UTC)

    with pytest.raises(InconsistentTimeError):
        SampleEntity(
            id="a",
            created_at=created,
            updated_at=created - timedelta(seconds=1),
        )
