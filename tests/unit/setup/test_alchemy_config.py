import dataclasses

import pytest

from answer_service.setup.configs.alchemy_config import SQLAlchemyConfig
from tests.unit.factories.config_factories import create_sqlalchemy_config


def test_optional_fields_have_sensible_defaults() -> None:
    config = SQLAlchemyConfig(
        pool_pre_ping=True,
        pool_recycle=30,
        pool_size=10,
        max_overflow=5,
        echo=False,
    )

    assert config.auto_flush is False
    assert config.expire_on_commit is False
    assert config.future is True


def test_config_is_immutable() -> None:
    config = create_sqlalchemy_config()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.echo = True  # type: ignore[misc]
