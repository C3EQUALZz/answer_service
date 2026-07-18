from typing import TYPE_CHECKING, override

from dature import EnvSource, F

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory
from answer_service.setup.configs.taskiq_config import TaskIQConfig

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class TaskIQEnvSourceFactory(SourceFactory):
    """Maps ``TASKIQ_*`` environment variables onto :class:`TaskIQConfig`."""

    @override
    def create(self) -> SourceProtocol:
        return EnvSource(
            field_mapping={
                F[TaskIQConfig].subject: "TASKIQ_SUBJECT",
                F[TaskIQConfig].stream_name: "TASKIQ_STREAM_NAME",
                F[TaskIQConfig].durable: "TASKIQ_DURABLE",
                F[TaskIQConfig].queue: "TASKIQ_QUEUE",
                F[TaskIQConfig].result_ex_time: "TASKIQ_RESULT_EX_TIME",
                F[TaskIQConfig].default_retry_count: "TASKIQ_DEFAULT_RETRY_COUNT",
                F[TaskIQConfig].default_delay: "TASKIQ_DEFAULT_DELAY",
                F[TaskIQConfig].use_jitter: "TASKIQ_USE_JITTER",
                F[TaskIQConfig].use_delay_exponent: "TASKIQ_USE_DELAY_EXPONENT",
                F[TaskIQConfig].max_delay_exponent: "TASKIQ_MAX_DELAY_EXPONENT",
            },
        )
