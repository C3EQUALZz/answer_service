from typing import Final

from fastapi import APIRouter, status

from answer_service.presentation.http.v1.common.exception_handler import ExceptionSchema

healthcheck_router: Final[APIRouter] = APIRouter(
    prefix="/healthcheck",
    tags=["Healthcheck"],
    include_in_schema=True,
)


@healthcheck_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ExceptionSchema},
    },
)
async def get_status() -> dict[str, str]:  # ruff:ignore[unused-async]
    """Liveness probe.

    Deliberately touches no dependency: a probe that fails when the database
    blinks gets the container killed instead of letting it recover.
    """
    return {"message": "ok", "status": "success"}
