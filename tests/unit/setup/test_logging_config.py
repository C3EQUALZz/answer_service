import dataclasses

import pytest

from answer_service.setup.configs.logging_config import LoggingConfig
from tests.unit.factories.config_factories import create_logging_config


def test_log_path_field_is_not_named_path() -> None:
    """The log path field must be ``log_path``, never ``path``.

    An unprefixed EnvSource matches fields by name, so a ``path`` field would
    bind to the ambient ``PATH`` variable.
    """
    field_names = {f.name for f in dataclasses.fields(LoggingConfig)}

    assert "log_path" in field_names
    assert "path" not in field_names


def test_defaults_are_console_info_without_file() -> None:
    config = LoggingConfig()

    assert config.render_json_logs is False
    assert config.log_path is None
    assert config.level == "INFO"


def test_config_is_immutable() -> None:
    config = create_logging_config()

    with pytest.raises(dataclasses.FrozenInstanceError):
        config.level = "DEBUG"  # type: ignore[misc]
