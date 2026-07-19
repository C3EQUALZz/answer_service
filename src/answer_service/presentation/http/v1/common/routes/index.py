from typing import Final

from fastapi import APIRouter, Request, status

from answer_service._version import __version__
from answer_service.presentation.http.v1.common.exception_handler import ExceptionSchema

index_router: Final[APIRouter] = APIRouter(tags=["Main"])


@index_router.get(
    "/",
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionSchema},
    },
)
def index(_: Request) -> dict[str, str]:
    """Root endpoint confirming the API is reachable."""
    return {"message": "Hello there! Welcome to answer_service", "version": __version__}
