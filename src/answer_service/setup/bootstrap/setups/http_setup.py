import logging
from typing import Final

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from answer_service.presentation.http.v1.common import ExceptionHandler
from answer_service.presentation.http.v1.common.routes import (
    healthcheck_router,
    index_router,
)
from answer_service.presentation.http.v1.middlewares import LoggingMiddleware
from answer_service.presentation.http.v1.routes import (
    conversation_router,
    indexing_router,
    search_router,
    statistics_router,
)
from answer_service.setup.configs.asgi_config import ASGIConfig

logger: Final[logging.Logger] = logging.getLogger(__name__)

API_V1_PREFIX: Final[str] = "/v1"


def setup_http_routes(app: FastAPI, /) -> None:
    """Registers every router on the application.

    The unversioned routes stay at the root: a probe or a landing page that
    moved with the API version would break every monitor on release.
    """
    app.include_router(index_router)
    app.include_router(healthcheck_router)

    router_v1: APIRouter = APIRouter(prefix=API_V1_PREFIX)
    router_v1.include_router(indexing_router)
    router_v1.include_router(conversation_router)
    router_v1.include_router(search_router)
    router_v1.include_router(statistics_router)
    app.include_router(router_v1)


def setup_http_middlewares(app: FastAPI, /, asgi_config: ASGIConfig) -> None:
    """Registers every middleware on the application."""
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            f"http://localhost:{asgi_config.port}",
            f"https://{asgi_config.host}:{asgi_config.port}",
            f"http://127.0.0.1:{asgi_config.port}",
            "http://127.0.0.1",
        ],
        allow_credentials=asgi_config.allow_credentials,
        allow_methods=asgi_config.allow_methods,
        allow_headers=asgi_config.allow_headers,
    )


def setup_exc_handlers(app: FastAPI, /) -> None:
    """Registers exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance to configure
    """
    exception_handler: ExceptionHandler = ExceptionHandler(app)
    exception_handler.setup_handlers()
