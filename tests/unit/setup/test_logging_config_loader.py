from pathlib import Path

import pytest
from dature.errors.exceptions import DatureConfigError

from answer_service.setup.bootstrap.loaders.logging_config_loader import (
    LoggingConfigLoader,
)
from tests.unit.factories.config_factories import create_logging_config
from tests.unit.factories.source_stubs import (
    empty_logging_source_stub,
    logging_source_stub,
)
from tests.unit.support import render_exception


def test_loads_and_maps_all_fields_from_env_names() -> None:
    config = LoggingConfigLoader(logging_source_stub()).load()

    assert config == create_logging_config(
        render_json_logs=True,
        log_path=Path("/var/log/app"),
        level="DEBUG",
    )


def test_uses_defaults_when_nothing_is_provided() -> None:
    config = LoggingConfigLoader(empty_logging_source_stub()).load()

    assert config == create_logging_config()


def test_rejects_an_unknown_log_level() -> None:
    loader = LoggingConfigLoader(logging_source_stub(LOG_LEVEL="TRACE"))

    with pytest.raises(DatureConfigError) as excinfo:
        loader.load()

    rendered = render_exception(excinfo.value)
    assert "LOG_LEVEL" in rendered or "level" in rendered
