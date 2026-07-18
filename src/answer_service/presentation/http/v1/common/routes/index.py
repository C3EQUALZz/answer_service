from typing import Final

from fastapi import APIRouter, Request

from answer_service._version import __version__

index_router: Final[APIRouter] = APIRouter(tags=["Main"])


@index_router.get("/")
def index(_: Request) -> dict[str, str]:
    """Root endpoint confirming the API is reachable."""
    return {"message": "Hello there! Welcome to answer_service", "version": __version__}
