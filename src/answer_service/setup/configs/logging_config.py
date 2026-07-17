from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass(slots=True, frozen=True)
class LoggingConfig:
    """Configuration for application logging (structlog + stdlib).

    Plain stdlib dataclass; env mapping lives in
    ``answer_service.setup.bootstrap.sources.logging_env_source_factory`` and
    the structlog wiring in ``answer_service.setup.bootstrap.setups``.

    Attributes:
        render_json_logs: Render logs as JSON instead of the console renderer.
        log_path: Directory or file to also write logs to; ``None`` disables
            file logging. Named ``log_path`` (not ``path``) so it never binds to
            the ubiquitous ``PATH`` environment variable.
        level: Root logging level.
    """

    render_json_logs: bool = False
    log_path: Path | None = None
    level: LogLevel = "INFO"
