import logging
from typing import Final

from taskiq import AsyncBroker, ScheduleSource, TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource

from answer_service.setup.configs.redis_config import RedisConfig

logger: Final[logging.Logger] = logging.getLogger(__name__)


def setup_schedule_source(redis_config: RedisConfig) -> ScheduleSource:
    """Creates the Redis-backed source of dynamically scheduled tasks."""
    return ListRedisScheduleSource(url=redis_config.schedule_source_uri)


def setup_scheduler(
    broker: AsyncBroker,
    schedule_source: ScheduleSource,
) -> TaskiqScheduler:
    """Creates the scheduler over both kinds of schedule.

    Two sources, because schedules arrive two ways. ``LabelScheduleSource``
    reads the cron declared at registration — that is what drives the outbox
    relay every minute. The Redis source holds schedules created at runtime and
    survives a restart, which a label-only scheduler could not.
    """
    logger.debug("Creating taskiq scheduler...")
    return TaskiqScheduler(
        broker=broker,
        sources=[
            LabelScheduleSource(broker),
            schedule_source,
        ],
    )
