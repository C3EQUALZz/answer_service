"""Dishka injection for test functions.

Lets a test declare the *port* it exercises and receive whatever the container
is wired to provide. Swapping the persistence technology then changes the
provider, not a single test — which is the point: a test that names
``SqlAlchemyOutboxGateway`` is a test of SQLAlchemy, not of the outbox.
"""

from collections.abc import Callable
from inspect import Parameter
from typing import Final

from dishka import AsyncContainer
from dishka.integrations.base import wrap_injection

CONTAINER_PARAM: Final = "dishka_container"


def inject[ReturnT, **FuncParams](
    func: Callable[FuncParams, ReturnT],
) -> Callable[FuncParams, ReturnT]:
    """Resolves ``FromDishka`` parameters, opening a request scope per test."""
    return wrap_injection(
        func=func,
        is_async=True,
        manage_scope=True,
        container_getter=lambda _args, kwargs: kwargs[CONTAINER_PARAM],
        additional_params=[
            Parameter(
                name=CONTAINER_PARAM,
                annotation=AsyncContainer,
                kind=Parameter.KEYWORD_ONLY,
            ),
        ],
    )
