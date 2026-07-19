from typing import Final

from dishka import Provider, Scope

from answer_service.application.commands.analytics.record_query.command import (
    RecordQueryCommand,
)
from answer_service.application.commands.analytics.record_query.handler import (
    RecordQueryHandler,
)
from answer_service.application.commands.indexing.enqueue_indexing.command import (
    EnqueueIndexingCommand,
)
from answer_service.application.commands.indexing.enqueue_indexing.handler import (
    EnqueueIndexingHandler,
)
from answer_service.application.commands.indexing.mark_indexing_failed.command import (
    MarkIndexingFailedCommand,
)
from answer_service.application.commands.indexing.mark_indexing_failed.handler import (
    MarkIndexingFailedHandler,
)
from answer_service.application.commands.indexing.mark_indexing_running.command import (
    MarkIndexingRunningCommand,
)
from answer_service.application.commands.indexing.mark_indexing_running.handler import (
    MarkIndexingRunningHandler,
)
from answer_service.application.commands.indexing.run_indexing.command import (
    RunIndexingCommand,
)
from answer_service.application.commands.indexing.run_indexing.handler import (
    RunIndexingHandler,
)
from answer_service.application.commands.outbox.relay_outbox.command import (
    RelayOutboxCommand,
)
from answer_service.application.commands.outbox.relay_outbox.handler import (
    RelayOutboxHandler,
)
from answer_service.application.commands.search.remove_qa_pair.command import (
    RemoveQAPairCommand,
)
from answer_service.application.commands.search.remove_qa_pair.handler import (
    RemoveQAPairHandler,
)
from answer_service.application.commands.search.upsert_qa_pair.command import (
    UpsertQAPairCommand,
)
from answer_service.application.commands.search.upsert_qa_pair.handler import (
    UpsertQAPairHandler,
)
from answer_service.application.common.mediator.markers import Command
from answer_service.application.common.mediator.sender import Sender
from answer_service.application.pipelines.events_pipeline import EventsPipeline
from answer_service.application.pipelines.transaction_pipeline import (
    TransactionPipeline,
)
from answer_service.application.queries.analytics.get_statistics.handler import (
    GetStatisticsHandler,
)
from answer_service.application.queries.analytics.get_statistics.query import (
    GetStatisticsQuery,
)
from answer_service.application.queries.analytics.list_unanswered_queries.handler import (
    ListUnansweredQueriesHandler,
)
from answer_service.application.queries.analytics.list_unanswered_queries.query import (
    ListUnansweredQueriesQuery,
)
from answer_service.application.queries.indexing.get_indexing_task.handler import (
    GetIndexingTaskHandler,
)
from answer_service.application.queries.indexing.get_indexing_task.query import (
    GetIndexingTaskQuery,
)
from answer_service.infrastructure.mediator import (
    Chain,
    ChainImpl,
    DishkaResolver,
    MediatorImpl,
    Registry,
    Resolver,
)


def make_registry() -> Registry:
    """Binds every request to its handler, and every command to its pipelines.

    Pipelines are registered against the ``Command`` marker rather than one
    command at a time. That is the whole point: a command added later is covered
    automatically, and cannot quietly run outside a transaction because someone
    forgot a line here.

    Queries are deliberately left uncovered — they mutate nothing, so opening a
    transaction around them would buy nothing and hold a connection for the
    duration of a report.

    The order below is the order of execution: the transaction opens first and
    commits last, with the events drained inside it. Reversed, events would be
    published after the commit and the outbox would stop being atomic with the
    state change it describes.
    """
    registry: Final[Registry] = Registry()

    registry.add_pipeline_handlers(Command, TransactionPipeline, EventsPipeline)

    registry.add_request_handler(EnqueueIndexingCommand, EnqueueIndexingHandler)
    registry.add_request_handler(MarkIndexingRunningCommand, MarkIndexingRunningHandler)
    registry.add_request_handler(RunIndexingCommand, RunIndexingHandler)
    registry.add_request_handler(MarkIndexingFailedCommand, MarkIndexingFailedHandler)
    registry.add_request_handler(RelayOutboxCommand, RelayOutboxHandler)
    registry.add_request_handler(UpsertQAPairCommand, UpsertQAPairHandler)
    registry.add_request_handler(RemoveQAPairCommand, RemoveQAPairHandler)
    registry.add_request_handler(RecordQueryCommand, RecordQueryHandler)

    registry.add_request_handler(GetIndexingTaskQuery, GetIndexingTaskHandler)
    registry.add_request_handler(GetStatisticsQuery, GetStatisticsHandler)
    registry.add_request_handler(
        ListUnansweredQueriesQuery,
        ListUnansweredQueriesHandler,
    )

    return registry


def mediator_provider() -> Provider:
    """The registry is process-wide; resolver and mediator are per request.

    The resolver wraps the *request-scoped* container, which is what makes every
    handler and pipeline it builds share that request's session and events
    collection.
    """
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide(make_registry, provides=Registry, scope=Scope.APP)
    provider.provide(source=ChainImpl, provides=Chain, scope=Scope.APP)
    provider.provide(source=DishkaResolver, provides=Resolver)
    provider.provide(source=MediatorImpl, provides=Sender)
    return provider
