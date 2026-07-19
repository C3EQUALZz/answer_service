from dataclasses import dataclass
from datetime import timedelta

SECONDS_PER_HOUR: int = 3600


@dataclass(slots=True, frozen=True)
class IndexingConfig:
    """Operational limits of a synchronization run.

    Attributes:
        stuck_after_seconds: How long a run may stay ``RUNNING`` before the
            reaper settles it as failed. It has to outlast the slowest
            legitimate run on *this* catalog: a task still working when the
            reaper reaches it would be failed underneath itself, and its sync
            would then commit against a task that is already terminal. The
            default is an hour, which is far beyond anything observed over a
            catalog of a few dozen pairs — raise it before indexing a large one,
            because the safe direction here is too long rather than too short.
    """

    stuck_after_seconds: int = SECONDS_PER_HOUR

    @property
    def stuck_after(self) -> timedelta:
        return timedelta(seconds=self.stuck_after_seconds)
