from collections import deque
from typing import Final

from dishka import Provider, Scope

from answer_service.domain.analytics.factories.query_log_factory import QueryLogFactory
from answer_service.domain.common.events_collection import EventsCollection
from answer_service.domain.indexing.factories.indexing_task_factory import (
    IndexingTaskFactory,
)
from answer_service.domain.indexing.factories.qa_pair_factory import QAPairFactory
from answer_service.domain.indexing.ports.id_generator import TaskIdGenerator
from answer_service.domain.indexing.services.sync_planner import SyncPlanner
from answer_service.domain.search.services.rrf_fusion import RrfFusion
from answer_service.infrastructure.adapters.common import UUID4TaskIdGenerator
from answer_service.setup.configs.search_config import SearchConfig


def make_events_collection() -> EventsCollection:
    return EventsCollection(events=deque())


def make_rrf_fusion(search_config: SearchConfig) -> RrfFusion:
    """Built by hand: ``k`` is a tuning constant, not a dependency.

    Provided as a source, dishka would try to resolve the ``int`` and fail. The
    weights come from configuration, so they can be swept against a deployment
    without a rebuild.
    """
    return RrfFusion(
        dense_weight=search_config.dense_weight,
        lexical_weight=search_config.lexical_weight,
    )


def domain_provider() -> Provider:
    """Domain factories, id generators and stateless domain services."""
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide(make_events_collection, provides=EventsCollection)
    provider.provide(source=UUID4TaskIdGenerator, provides=TaskIdGenerator)
    provider.provide(source=QAPairFactory)
    provider.provide(source=IndexingTaskFactory)
    provider.provide(source=QueryLogFactory)
    provider.provide(source=SyncPlanner, scope=Scope.APP)
    provider.provide(make_rrf_fusion, provides=RrfFusion, scope=Scope.APP)
    return provider
