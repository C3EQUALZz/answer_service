import dataclasses

import pytest

from answer_service.setup.configs.asgi_config import ASGIConfig
from tests.unit.factories.config_factories import create_asgi_config


def test_defaults_bind_all_interfaces_on_8080() -> None:
    config = ASGIConfig()

    assert config.host == "0.0.0.0"  # ruff:ignore[hardcoded-bind-all-interfaces]
    assert config.port == 8080
    assert config.fastapi_debug is True
    assert config.allow_credentials is False


def test_default_cors_lists_are_populated() -> None:
    config = ASGIConfig()

    assert "GET" in config.allow_methods
    assert "Authorization" in config.allow_headers


def test_config_is_immutable() -> None:
    config = create_asgi_config()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.port = 9000  # type: ignore[misc]
