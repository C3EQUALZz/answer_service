import pytest
from dature.errors.exceptions import DatureConfigError

from answer_service.setup.bootstrap.loaders.asgi_config_loader import ASGIConfigLoader
from tests.unit.factories.config_factories import create_asgi_config
from tests.unit.factories.source_stubs import asgi_source_stub
from tests.unit.support import render_exception


def test_loads_and_maps_all_fields_from_env_names() -> None:
    config = ASGIConfigLoader(asgi_source_stub()).load()

    assert config == create_asgi_config()


@pytest.mark.parametrize("port", ("0", "65536", "-1"))
def test_rejects_port_outside_the_valid_range(port: str) -> None:
    with pytest.raises(DatureConfigError) as excinfo:
        ASGIConfigLoader(asgi_source_stub(UVICORN_PORT=port)).load()

    assert "UVICORN_PORT must be between 1 and 65535" in render_exception(excinfo.value)


def test_cors_lists_are_not_env_driven_and_keep_defaults() -> None:
    config = ASGIConfigLoader(asgi_source_stub()).load()

    assert config.allow_methods == ["GET", "POST", "PUT", "PATCH", "DELETE"]
    assert "Authorization" in config.allow_headers
