from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class ASGIConfig:
    """Configuration container for ASGI server settings.

    Plain stdlib dataclass; env mapping lives in
    ``answer_service.setup.bootstrap.sources.asgi_env_source_factory`` and port
    validation in ``answer_service.setup.bootstrap.loaders.asgi_config_loader``.

    Attributes:
        host: Interface to bind the server to (e.g. '0.0.0.0' or 'localhost').
        port: TCP port to listen on.
        fastapi_debug: Enable FastAPI debug output.
        allow_credentials: Enable the CORS ``allow_credentials`` flag.
        allow_methods: CORS allowed HTTP methods.
        allow_headers: CORS allowed request headers.
    """

    host: str = "0.0.0.0"  # ruff:ignore[hardcoded-bind-all-interfaces]  # nosec B104
    port: int = 8080
    fastapi_debug: bool = True
    allow_credentials: bool = False
    allow_methods: list[str] = field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE"],
    )
    allow_headers: list[str] = field(
        default_factory=lambda: [
            "Authorization",
            "Content-Type",
            "Cache-Control",
            "Set-Cookie",
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Origin",
        ],
    )
