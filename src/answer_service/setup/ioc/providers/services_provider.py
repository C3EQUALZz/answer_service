from typing import Final

from dishka import Provider, Scope

from answer_service.application.common.services import HybridSearchService


def services_provider() -> Provider:
    """Application services shared by more than one use case.

    Per request because their collaborators are: the retrievers read through the
    request's own session and the catalog gateway with it.
    """
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide(source=HybridSearchService)
    return provider
