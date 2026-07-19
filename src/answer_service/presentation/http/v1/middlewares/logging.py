import logging
import time
from typing import Final, override

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger: Final[logging.Logger] = logging.getLogger(__name__)

MILLISECONDS_PER_SECOND: Final[int] = 1000


class LoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request and the status it answered with."""

    @override
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started_at = time.perf_counter()
        logger.info("http: %s %s", request.method, request.url.path)

        response: Response = await call_next(request)

        took_ms = round(
            (time.perf_counter() - started_at) * MILLISECONDS_PER_SECOND,
        )
        logger.info(
            "http: %s %s -> %d in %d ms",
            request.method,
            request.url.path,
            response.status_code,
            took_ms,
        )
        return response
