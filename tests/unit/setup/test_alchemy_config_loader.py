import pytest
from dature.errors.exceptions import DatureConfigError

from answer_service.setup.bootstrap.loaders.alchemy_config_loader import (
    SQLAlchemyConfigLoader,
)
from tests.unit.factories.config_factories import create_sqlalchemy_config
from tests.unit.factories.source_stubs import sqlalchemy_source_stub
from tests.unit.support import render_exception


def test_loads_required_fields_and_applies_defaults() -> None:
    config = SQLAlchemyConfigLoader(sqlalchemy_source_stub()).load()

    assert config == create_sqlalchemy_config()


def test_rejects_pool_recycle_below_minimum() -> None:
    loader = SQLAlchemyConfigLoader(sqlalchemy_source_stub(DB_POOL_RECYCLE="0"))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "DB_POOL_RECYCLE must be at least 1 minutes" in render_exception(excinfo.value)


@pytest.mark.parametrize("pool_size", ("0", "1001"))
def test_rejects_pool_size_outside_range(pool_size: str) -> None:
    loader = SQLAlchemyConfigLoader(sqlalchemy_source_stub(DB_POOL_SIZE=pool_size))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "DB_POOL_SIZE must be between 1 and 1000" in render_exception(excinfo.value)


def test_rejects_negative_max_overflow() -> None:
    loader = SQLAlchemyConfigLoader(sqlalchemy_source_stub(DB_POOL_MAX_OVERFLOW="-1"))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    assert "DB_POOL_MAX_OVERFLOW must be at least 0" in render_exception(excinfo.value)


def test_accepts_zero_max_overflow_boundary() -> None:
    config = SQLAlchemyConfigLoader(
        sqlalchemy_source_stub(DB_POOL_MAX_OVERFLOW="0")
    ).load()

    assert config.max_overflow == 0
