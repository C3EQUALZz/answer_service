from typing import Final

from fastapi import APIRouter, status

healthcheck_router: Final[APIRouter] = APIRouter(
    prefix="/healthcheck",
    tags=["Healthcheck"],
    include_in_schema=True,
)


@healthcheck_router.get("/", status_code=status.HTTP_200_OK)
async def get_status() -> dict[str, str]:  # ruff:ignore[unused-async]
    """Liveness probe.

    Deliberately touches no dependency: a probe that fails when the database
    blinks gets the container killed instead of letting it recover.
    """
    return {"message": "ok", "status": "success"}
