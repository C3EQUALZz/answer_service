from typing import Final

from dishka import Provider, Scope

from answer_service.application.common.ports.mappers import (
    QAPairDocumentMapper,
    SourceRowMapper,
)
from answer_service.infrastructure.mappers import (
    AdaptixIndexMetadataMapper,
    AdaptixQAPairDocumentMapper,
    AdaptixSourceRowMapper,
    IndexMetadataMapper,
    IndexingTaskViewMapper,
    QueryLogEntryMapper,
    SqlAlchemyIndexingTaskViewMapper,
    SqlAlchemyQueryLogEntryMapper,
)


def mappers_provider() -> Provider:
    """Binds every mapping port to the adapter that performs it.

    ``APP`` scope, unlike the gateways: a mapper holds no session and no events
    collection, and the adaptix converters it calls are compiled once at import
    time. Rebuilding one per request would allocate for nothing.
    """
    provider: Final[Provider] = Provider(scope=Scope.APP)

    provider.provide(source=AdaptixSourceRowMapper, provides=SourceRowMapper)
    provider.provide(
        source=AdaptixQAPairDocumentMapper,
        provides=QAPairDocumentMapper,
    )
    provider.provide(
        source=AdaptixIndexMetadataMapper,
        provides=IndexMetadataMapper,
    )
    provider.provide(
        source=SqlAlchemyIndexingTaskViewMapper,
        provides=IndexingTaskViewMapper,
    )
    provider.provide(
        source=SqlAlchemyQueryLogEntryMapper,
        provides=QueryLogEntryMapper,
    )

    return provider
