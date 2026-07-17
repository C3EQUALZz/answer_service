import dataclasses

import pytest

from tests.unit.factories.config_factories import create_postgres_config


def test_uri_uses_driver_credentials_and_database() -> None:
    config = create_postgres_config(
        user="app",
        password="s3cr3t",
        host="db.internal",
        port=6432,
        db_name="prod",
        driver="asyncpg",
    )

    assert config.uri == "postgresql+asyncpg://app:s3cr3t@db.internal:6432/prod"


def test_uri_reflects_the_configured_driver() -> None:
    config = create_postgres_config(driver="psycopg")

    assert config.uri.startswith("postgresql+psycopg://")


def test_config_is_immutable() -> None:
    config = create_postgres_config()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.port = 1  # type: ignore[misc]
