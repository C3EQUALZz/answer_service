from typing import Final

from dishka import Provider, Scope
from taskiq import ScheduleSource

from answer_service.application.common.ports.task_manager.task_manager import (
    TaskScheduler,
)
from answer_service.infrastructure.task_manager.task_iq_task_scheduler import (
    TaskIQTaskScheduler,
)
from answer_service.setup.bootstrap.setups.scheduler_setup import setup_schedule_source


def task_manager_provider() -> Provider:
    """The schedule source is process-wide; the scheduler adapter per request."""
    provider: Final[Provider] = Provider(scope=Scope.REQUEST)
    provider.provide(setup_schedule_source, provides=ScheduleSource, scope=Scope.APP)
    provider.provide(source=TaskIQTaskScheduler, provides=TaskScheduler)
    return provider
