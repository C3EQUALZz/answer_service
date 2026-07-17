import pytest
from dature.errors.exceptions import DatureConfigError

from answer_service.setup.bootstrap.loaders.postgres_config_loader import (
    PostgresConfigLoader,
)
from tests.unit.factories.config_factories import create_postgres_config
from tests.unit.factories.source_stubs import postgres_source_stub
from tests.unit.factories.stub_source_factory import StubSourceFactory
from tests.unit.support import render_exception


def test_loads_and_maps_all_fields_from_env_names() -> None:
    config = PostgresConfigLoader(postgres_source_stub()).load()

    assert config == create_postgres_config()


@pytest.mark.parametrize("port", ("0", "65536", "-1"))
def test_rejects_port_outside_the_valid_range(port: str) -> None:
    with pytest.raises(DatureConfigError) as excinfo:
        PostgresConfigLoader(postgres_source_stub(POSTGRES_PORT=port)).load()

    assert "POSTGRES_PORT must be between 1 and 65535" in render_exception(excinfo.value)


def test_accepts_the_port_range_boundaries() -> None:
    assert PostgresConfigLoader(postgres_source_stub(POSTGRES_PORT="1")).load().port == 1
    assert (
        PostgresConfigLoader(postgres_source_stub(POSTGRES_PORT="65535")).load().port
        == 65535
    )


def test_password_is_masked_in_error_output() -> None:
    stub = postgres_source_stub(
        POSTGRES_PASSWORD="TOP-SECRET-VALUE",
        POSTGRES_PORT="999999",
    )

    with pytest.raises(DatureConfigError) as excinfo:
        PostgresConfigLoader(stub).load()

    assert "TOP-SECRET-VALUE" not in render_exception(excinfo.value)


def test_loader_accepts_data_keyed_directly_by_field_name() -> None:
    """A stub keyed directly by field name (no env mapping) also works.

    The loader depends only on the SourceFactory protocol.
    """
    stub = StubSourceFactory(
        {
            "user": "alice",
            "password": "pw",
            "host": "h",
            "port": "5432",
            "db_name": "d",
            "driver": "asyncpg",
        },
    )

    config = PostgresConfigLoader(stub).load()

    assert config.user == "alice"
    assert config.uri == "postgresql+asyncpg://alice:pw@h:5432/d"
