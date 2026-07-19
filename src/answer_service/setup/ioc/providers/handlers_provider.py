from typing import Final

from dishka import Provider, Scope

from answer_service.application.commands.indexing.enqueue_indexing.handler import (
    EnqueueIndexingHandler,
)
from answer_service.application.commands.indexing.mark_indexing_failed.handler import (
    MarkIndexingFailedHandler,
)
from answer_service.application.commands.indexing.mark_indexing_running.handler import (
    MarkIndexingRunningHandler,
)
from answer_service.application.commands.indexing.run_indexing.handler import (
    RunIndexingHandler,
)
from answer_service.application.commands.outbox.relay_outbox.handler import (
    RelayOutboxHandler,
)
from answer_service.application.commands.search.remove_qa_pair.handler import (
    RemoveQAPairHandler,
)
from answer_service.application.commands.search.upsert_qa_pair.handler import (
    UpsertQAPairHandler,
)
from answer_service.application.queries.analytics.get_statistics.handler import (
    GetStatisticsHandler,
)
from answer_service.application.queries.analytics.list_unanswered_queries.handler import (
    ListUnansweredQueriesHandler,
)
from answer_service.application.queries.conversation.ask_question.handler import (
    AskQuestionHandler,
)
from answer_service.application.queries.indexing.get_indexing_task.handler import (
    GetIndexingTaskHandler,
)
from answer_service.application.queries.search.search_qa_pairs.handler import (
    SearchQAPairsHandler,
)


def handlers_provider() -> Provider:
    """Every command and query handler.

    Resolved per request because their collaborators are: the mediator asks for
    a fresh handler on each dispatch, so a longer-lived one would hold a session
    belonging to a request that has already finished.
    """
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide_all(
        EnqueueIndexingHandler,
        MarkIndexingRunningHandler,
        RunIndexingHandler,
        MarkIndexingFailedHandler,
        RelayOutboxHandler,
        UpsertQAPairHandler,
        RemoveQAPairHandler,
        GetIndexingTaskHandler,
        GetStatisticsHandler,
        ListUnansweredQueriesHandler,
        SearchQAPairsHandler,
        AskQuestionHandler,
    )
    return provider
