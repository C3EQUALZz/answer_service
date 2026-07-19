from typing import Final

from dishka import Provider, Scope

from answer_service.application.common.ports.embedding import Embedder
from answer_service.application.common.ports.gateways import (
    AnalyticsCommandGateway,
    AnalyticsQueryGateway,
    IndexingTaskCommandGateway,
    IndexingTaskQueryGateway,
    QACatalogCommandGateway,
    QACatalogQueryGateway,
)
from answer_service.application.common.ports.outbox import (
    EventBus,
    EventSerializer,
    OutboxCommandGateway,
    OutboxPublisher,
)
from answer_service.application.common.ports.search import (
    DenseRetriever,
    LexicalRetriever,
    SearchIndexWriter,
)
from answer_service.application.common.ports.source_file.source_file_reader import (
    SourceFileReader,
)
from answer_service.application.common.ports.source_file.source_file_storage import (
    SourceFileStorage,
)
from answer_service.application.common.ports.transaction_manager import (
    TransactionManager,
)
from answer_service.infrastructure.adapters.common import (
    OutboxEventBus,
    RetortEventSerializer,
)
from answer_service.infrastructure.adapters.langchain.langchain_embedder import (
    LangChainEmbedder,
)
from answer_service.infrastructure.adapters.messaging import (
    TaskSchedulerOutboxPublisher,
)
from answer_service.infrastructure.adapters.persistence import (
    SqlAlchemyAnalyticsGateway,
    SqlAlchemyIndexingTaskGateway,
    SqlAlchemyIndexingTaskQueryGateway,
    SqlAlchemyOutboxGateway,
    SqlAlchemyQACatalogGateway,
    SqlAlchemyTransactionManager,
)
from answer_service.infrastructure.adapters.search.postgres_lexical_retriever import (
    PostgresLexicalRetriever,
)
from answer_service.infrastructure.adapters.search.qdrant_dense_retriever import (
    QdrantDenseRetriever,
)
from answer_service.infrastructure.adapters.search.qdrant_search_index_writer import (
    QdrantSearchIndexWriter,
)
from answer_service.infrastructure.adapters.source_file import (
    LocalSourceFileStorage,
    PolarsSourceFileReader,
)


def gateways_provider() -> Provider:
    """Binds every application port to the adapter that implements it.

    ``REQUEST`` scope throughout, because each of these is built around the
    request-scoped session or events collection. The two search adapters could
    be process-wide, but they are resolved alongside the rest and cost only an
    attribute assignment to build.
    """
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)

    provider.provide(source=SqlAlchemyTransactionManager, provides=TransactionManager)

    provider.provide(
        source=SqlAlchemyIndexingTaskGateway,
        provides=IndexingTaskCommandGateway,
    )
    provider.provide(
        source=SqlAlchemyIndexingTaskQueryGateway,
        provides=IndexingTaskQueryGateway,
    )
    provider.provide(
        source=SqlAlchemyQACatalogGateway,
        provides=QACatalogCommandGateway,
    )
    provider.provide(
        source=SqlAlchemyQACatalogGateway,
        provides=QACatalogQueryGateway,
    )
    provider.provide(
        source=SqlAlchemyAnalyticsGateway,
        provides=AnalyticsCommandGateway,
    )
    provider.provide(
        source=SqlAlchemyAnalyticsGateway,
        provides=AnalyticsQueryGateway,
    )

    provider.provide(source=SqlAlchemyOutboxGateway, provides=OutboxCommandGateway)
    provider.provide(source=RetortEventSerializer, provides=EventSerializer)
    provider.provide(source=TaskSchedulerOutboxPublisher, provides=OutboxPublisher)
    provider.provide(source=OutboxEventBus, provides=EventBus)

    provider.provide(source=LangChainEmbedder, provides=Embedder)
    provider.provide(source=QdrantSearchIndexWriter, provides=SearchIndexWriter)
    provider.provide(source=QdrantDenseRetriever, provides=DenseRetriever)
    provider.provide(source=PostgresLexicalRetriever, provides=LexicalRetriever)

    provider.provide(source=LocalSourceFileStorage, provides=SourceFileStorage)
    provider.provide(source=PolarsSourceFileReader, provides=SourceFileReader)

    return provider
