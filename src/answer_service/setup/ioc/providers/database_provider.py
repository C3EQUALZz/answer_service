from typing import Final

from dishka import Provider, Scope
from sqlalchemy.ext.asyncio import AsyncSession

from answer_service.setup.ioc.providers.sqlalchemy_provider import (
    get_engine,
    get_session,
    get_sessionmaker,
)


def database_provider() -> Provider:
    """Engine and session factory live for the process; sessions per request.

    A session is a unit of work and carries an identity map, so sharing one
    across requests would leak one request's uncommitted state into another.
    """
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide(get_engine, scope=Scope.APP)
    provider.provide(get_sessionmaker, scope=Scope.APP)
    provider.provide(get_session, provides=AsyncSession)
    return provider
