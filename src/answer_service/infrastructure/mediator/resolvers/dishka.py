from typing import Final, cast, override

from dishka import AsyncContainer

from answer_service.infrastructure.mediator.interfaces.resolver import Handler, Resolver


class DishkaResolver(Resolver):
    """Resolver backed by a dishka container.

    Takes the request-scoped container, so every handler and pipeline built for
    one request shares that request's session and events collection.
    """

    def __init__(self, container: AsyncContainer) -> None:
        self._container: Final[AsyncContainer] = container

    @override
    async def resolve[TDependency: Handler](
        self,
        dependency_type: type[TDependency],
    ) -> TDependency:
        return cast("TDependency", await self._container.get(dependency_type))
