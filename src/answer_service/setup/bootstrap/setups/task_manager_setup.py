import logging
from typing import Final

from taskiq import AsyncBroker, async_shared_broker
from taskiq.middlewares import SmartRetryMiddleware
from taskiq_nats import PullBasedJetStreamBroker
from taskiq_redis import RedisAsyncResultBackend

from answer_service.infrastructure.task_manager.tasks import (
    setup_indexing_tasks,
    setup_outbox_tasks,
)
from answer_service.setup.configs.nats_config import NatsConfig
from answer_service.setup.configs.redis_config import RedisConfig
from answer_service.setup.configs.taskiq_config import TaskIQConfig

logger: Final[logging.Logger] = logging.getLogger(__name__)


def setup_task_manager(
    taskiq_config: TaskIQConfig,
    nats_config: NatsConfig,
    redis_config: RedisConfig,
) -> AsyncBroker:
    """Creates the taskiq JetStream broker with a Redis result backend.

    Pull-based rather than push-based: work is pulled by whichever replica is
    free, so a slow worker cannot have messages forced onto it while another
    sits idle. The durable consumer means a restarted worker resumes its queue
    instead of losing the tasks that arrived while it was down.

    Results live in Redis rather than NATS because they are read by the HTTP
    layer for task-status polling, which wants cheap key lookups with a TTL.
    """
    logger.debug("Creating taskiq broker...")

    broker: AsyncBroker = PullBasedJetStreamBroker(
        servers=nats_config.uri,
        subject=taskiq_config.subject,
        stream_name=taskiq_config.stream_name,
        durable=taskiq_config.durable,
        queue=taskiq_config.queue,
    ).with_result_backend(
        RedisAsyncResultBackend(
            redis_url=redis_config.worker_uri,
            result_ex_time=taskiq_config.result_ex_time,
        ),
    )

    async_shared_broker.default_broker(broker)
    logger.debug("Taskiq broker created and set as default")
    return broker


def setup_task_manager_middlewares(
    broker: AsyncBroker,
    taskiq_config: TaskIQConfig,
) -> AsyncBroker:
    """Applies the retry policy to the broker.

    Jitter matters here specifically because replicas fail together — a NATS
    blip hits every worker at once, and without jitter they would all retry in
    the same instant and reproduce the outage.
    """
    return broker.with_middlewares(
        SmartRetryMiddleware(
            default_retry_count=taskiq_config.default_retry_count,
            default_delay=taskiq_config.default_delay,
            use_jitter=taskiq_config.use_jitter,
            use_delay_exponent=taskiq_config.use_delay_exponent,
            max_delay_exponent=taskiq_config.max_delay_exponent,
        ),
    )


def setup_task_manager_tasks(broker: AsyncBroker) -> None:
    """Registers every background task on the broker.

    The scheduler resolves a task by the name used at registration, and
    ``TaskIQTaskScheduler`` derives that name from the ``TaskKey`` half of a
    task id. A task missing here therefore fails at schedule time, not at
    startup — which is why registration lives in one place.
    """
    setup_indexing_tasks(broker)
    setup_outbox_tasks(broker)
