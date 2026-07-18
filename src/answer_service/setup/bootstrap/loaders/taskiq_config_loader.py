from typing import TYPE_CHECKING, Final, override

from dature import V, load

from answer_service.setup.bootstrap.loaders.loader import ConfigLoader
from answer_service.setup.configs.taskiq_config import TaskIQConfig

from .consts import DELAY_MIN, MAX_DELAY_EXPONENT_MIN, RETRY_COUNT_MIN

if TYPE_CHECKING:
    from collections.abc import Iterable

    from dature.validators.root import RootPredicate

    from answer_service.setup.bootstrap.sources.source_factory import SourceFactory


class TaskIQConfigLoader(ConfigLoader[TaskIQConfig]):
    """``dature``-backed loader for :class:`TaskIQConfig`."""

    def __init__(self, source_factory: SourceFactory) -> None:
        self._source_factory: Final[SourceFactory] = source_factory

    @override
    def load(self) -> TaskIQConfig:
        return load(
            self._source_factory.create(),
            schema=TaskIQConfig,
            root_validators=self._root_validators(),
        )

    @staticmethod
    def _root_validators() -> Iterable[RootPredicate]:
        return (
            V.root(
                lambda c: c.default_retry_count >= RETRY_COUNT_MIN,
                error_message=(
                    f"TASKIQ_DEFAULT_RETRY_COUNT must be at least {RETRY_COUNT_MIN}"
                ),
            ),
            V.root(
                lambda c: c.default_delay >= DELAY_MIN,
                error_message=f"TASKIQ_DEFAULT_DELAY must be at least {DELAY_MIN}",
            ),
            V.root(
                lambda c: c.max_delay_exponent >= MAX_DELAY_EXPONENT_MIN,
                error_message=(
                    f"TASKIQ_MAX_DELAY_EXPONENT must be at least {MAX_DELAY_EXPONENT_MIN}"
                ),
            ),
            V.root(
                lambda c: c.result_ex_time > 0,
                error_message="TASKIQ_RESULT_EX_TIME must be positive",
            ),
        )
