from pathlib import Path

import pytest
from taskiq import AsyncBroker, InMemoryBroker

from answer_service.infrastructure.adapters.common import RetortEventSerializer
from answer_service.infrastructure.adapters.source_file import (
    LocalSourceFileStorage,
    PolarsSourceFileReader,
)
from answer_service.infrastructure.task_manager.task_iq_task_scheduler import (
    TaskIQTaskScheduler,
)
from answer_service.setup.configs.storage_config import StorageConfig
from tests.unit.stubs.infrastructure import StubScheduleSource


@pytest.fixture()
def storage(tmp_path: Path) -> LocalSourceFileStorage:
    return LocalSourceFileStorage(StorageConfig(directory=tmp_path / "uploads"))


@pytest.fixture()
def reader() -> PolarsSourceFileReader:
    return PolarsSourceFileReader()


@pytest.fixture()
def in_memory_broker() -> InMemoryBroker:
    """A broker of this test's own, distinct from the session-wide recorder."""
    return InMemoryBroker()


@pytest.fixture()
def scheduler(in_memory_broker: AsyncBroker) -> TaskIQTaskScheduler:
    return TaskIQTaskScheduler(in_memory_broker, StubScheduleSource())


@pytest.fixture()
def serializer() -> RetortEventSerializer:
    return RetortEventSerializer()
