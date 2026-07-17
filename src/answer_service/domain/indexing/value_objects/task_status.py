from enum import StrEnum, auto


class IndexingTaskStatus(StrEnum):
    QUEUED = auto()
    RUNNING = auto()
    SUCCEEDED = auto()
    FAILED = auto()

    @property
    def is_terminal(self) -> bool:
        return self in {IndexingTaskStatus.SUCCEEDED, IndexingTaskStatus.FAILED}
