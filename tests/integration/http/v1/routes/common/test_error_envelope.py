"""The shape every error answer takes, through the real application.

One envelope across the whole API is the point: a client that can read one
failure can read all of them. Request validation is the case that has to be
asserted rather than assumed — FastAPI answers it with its own handler and its
own body unless the service claims the exception explicitly.
"""

import pytest
from httpx import AsyncClient

pytestmark = [
    pytest.mark.asyncio(loop_scope="session"),
]

SEARCH_URL = "/v1/search/"
STATISTICS_URL = "/v1/statistics/"
TASKS_URL = "/v1/indexing/tasks/not-a-uuid"


async def test_a_malformed_body_answers_the_services_own_envelope(
    client: AsyncClient,
) -> None:
    """Not FastAPI's ``{"detail": [...]}``.

    ``RequestValidationError`` is unrelated to ``pydantic.ValidationError`` by
    type, so it reaches the service's handler only because it is registered
    there by name — and silently stops if that entry is ever dropped.
    """
    response = await client.post(SEARCH_URL, json={"query": "hello", "top_k": 999})

    assert response.status_code == 422
    assert set(response.json()) == {"description", "details"}


async def test_a_malformed_query_parameter_answers_the_same_envelope(
    client: AsyncClient,
) -> None:
    response = await client.get(STATISTICS_URL, params={"days": 0})

    assert response.status_code == 422
    assert set(response.json()) == {"description", "details"}


async def test_a_malformed_path_parameter_answers_the_same_envelope(
    client: AsyncClient,
) -> None:
    response = await client.get(TASKS_URL)

    assert response.status_code == 422
    assert set(response.json()) == {"description", "details"}


async def test_the_offending_fields_are_reported_back(client: AsyncClient) -> None:
    """The details are what make a 422 actionable rather than just a refusal."""
    response = await client.post(SEARCH_URL, json={"query": "hello", "top_k": 999})

    locations = [error["loc"] for error in response.json()["details"]]

    assert ["body", "top_k"] in locations


async def test_a_validation_failure_names_no_server_path(client: AsyncClient) -> None:
    """``str(RequestValidationError)`` renders the handler's file and line.

    Handing that back would put a filesystem path from the running container
    into an unauthenticated response, which is the same reason 5xx messages are
    replaced before they are sent.
    """
    response = await client.post(SEARCH_URL, json={"query": "hello", "top_k": 999})

    description = response.json()["description"]

    assert 'File "' not in description
    assert ".py" not in description


async def test_a_domain_refusal_keeps_the_plain_envelope(client: AsyncClient) -> None:
    """400 carries no ``details``: there is no field list behind it."""
    response = await client.post(SEARCH_URL, json={"query": "   "})

    assert response.status_code == 400
    assert set(response.json()) == {"description"}
