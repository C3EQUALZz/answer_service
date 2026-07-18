"""The liveness probe and the index route.

Both answer without touching a dependency. That is the property under test: a
probe that fails when the database blinks gets the container killed instead of
letting it recover.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio(loop_scope="session")

HEALTHCHECK_URL = "/healthcheck/"
INDEX_URL = "/"


async def test_the_probe_answers_ok(client: AsyncClient) -> None:
    response = await client.get(HEALTHCHECK_URL)

    assert response.status_code == 200
    assert response.json() == {"message": "ok", "status": "success"}


async def test_the_probe_needs_no_database(
    client: AsyncClient,
    postgres_container: object,
) -> None:
    """Deliberately requested without ``clean_tables``: no schema, still healthy."""
    del postgres_container

    response = await client.get(HEALTHCHECK_URL)

    assert response.status_code == 200


async def test_the_probe_stays_healthy_across_calls(client: AsyncClient) -> None:
    """Monitors poll it constantly; it must not depend on any per-call state."""
    responses = [await client.get(HEALTHCHECK_URL) for _ in range(3)]

    assert [response.status_code for response in responses] == [200, 200, 200]


async def test_the_probe_is_not_versioned(client: AsyncClient) -> None:
    """Moving it with the API version would break every monitor on release."""
    versioned = await client.get(f"/v1{HEALTHCHECK_URL}")

    assert versioned.status_code == 404


async def test_the_index_route_names_the_service(client: AsyncClient) -> None:
    response = await client.get(INDEX_URL)

    assert response.status_code == 200
    body = response.json()
    assert "answer_service" in body["message"]
    assert body["version"]


async def test_an_unknown_route_is_a_not_found(client: AsyncClient) -> None:
    response = await client.get("/v1/nothing-here")

    assert response.status_code == 404
