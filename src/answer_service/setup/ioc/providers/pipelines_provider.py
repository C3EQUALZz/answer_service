from typing import Final

from dishka import Provider, Scope

from answer_service.application.pipelines.events_pipeline import EventsPipeline
from answer_service.application.pipelines.query_recording_pipeline import (
    QueryRecordingPipeline,
)
from answer_service.application.pipelines.transaction_pipeline import (
    TransactionPipeline,
)


def pipelines_provider() -> Provider:
    """Pipelines are per request: each wraps that request's own unit of work."""
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide(source=TransactionPipeline)
    provider.provide(source=EventsPipeline)
    provider.provide(source=QueryRecordingPipeline)
    return provider
