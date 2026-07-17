from typing import TYPE_CHECKING, Final, override

from answer_service.application.commands.indexing.run_indexing.command import (
    RunIndexingCommand,
)
from answer_service.application.common.mediator.handlers import CommandHandler
from answer_service.application.common.ports.gateways import (
    IndexingTaskCommandGateway,
    QACatalogCommandGateway,
    QACatalogQueryGateway,
)
from answer_service.application.common.ports.source_file.source_file_reader import (
    SourceFileReader,
)
from answer_service.application.common.ports.source_file.source_file_storage import (
    SourceFileStorage,
)
from answer_service.application.common.ports.source_file.source_row import SourceRow
from answer_service.application.error import IndexingTaskNotFoundError
from answer_service.domain.indexing.factories.qa_pair_factory import QAPairFactory
from answer_service.domain.indexing.services.sync_planner import SyncPlanner
from answer_service.domain.indexing.value_objects.answer import Answer
from answer_service.domain.indexing.value_objects.category import Category
from answer_service.domain.indexing.value_objects.desired_pair import DesiredPair
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from answer_service.domain.indexing.value_objects.qa_content import QAContent
from answer_service.domain.indexing.value_objects.question import Question
from answer_service.domain.indexing.value_objects.sync_plan import SyncPlan
from answer_service.domain.indexing.value_objects.sync_stats import SyncStats

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.source_reference import (
        SourceReference,
    )


class RunIndexingHandler(CommandHandler[RunIndexingCommand, None]):
    """Executes a sync run against the catalog (the search stores follow via events).

    Stays inside the unit-of-work provided by the transaction pipeline: it only
    mutates the catalog and drives the task's lifecycle. Domain events emitted by
    the aggregates are published (and turned into Qdrant/FTS updates) downstream;
    failure recording is a separate command, so it survives a work rollback.
    """

    def __init__(  # ruff:ignore[too-many-arguments, too-many-positional-arguments]
        self,
        task_gateway: IndexingTaskCommandGateway,
        source_storage: SourceFileStorage,
        source_reader: SourceFileReader,
        catalog_command: QACatalogCommandGateway,
        catalog_query: QACatalogQueryGateway,
        qa_pair_factory: QAPairFactory,
        sync_planner: SyncPlanner,
    ) -> None:
        self._task_gateway: Final[IndexingTaskCommandGateway] = task_gateway
        self._source_storage: Final[SourceFileStorage] = source_storage
        self._source_reader: Final[SourceFileReader] = source_reader
        self._catalog_command: Final[QACatalogCommandGateway] = catalog_command
        self._catalog_query: Final[QACatalogQueryGateway] = catalog_query
        self._qa_pair_factory: Final[QAPairFactory] = qa_pair_factory
        self._sync_planner: Final[SyncPlanner] = sync_planner

    @override
    async def handle(self, command: RunIndexingCommand) -> None:
        task = await self._task_gateway.read_by_id(command.task_id)
        if task is None:
            msg = f"Indexing task '{command.task_id}' not found."
            raise IndexingTaskNotFoundError(msg)

        task.start()
        stats = await self._run_sync(task.source)
        task.complete(stats)
        await self._task_gateway.update(task)

    async def _run_sync(self, source: SourceReference) -> SyncStats:
        content = await self._source_storage.open(source)
        rows = await self._source_reader.read_rows(content=content)
        desired = [self._to_desired_pair(row) for row in rows]

        manifest = await self._catalog_query.read_fingerprints()
        plan = self._sync_planner.plan(desired=desired, current=manifest)

        await self._apply(plan)
        return plan.stats()

    @staticmethod
    def _to_desired_pair(row: SourceRow) -> DesiredPair:
        return DesiredPair(
            external_id=ExternalId(value=row.external_id),
            content=QAContent(
                question=Question(content=row.question),
                answer=Answer(content=row.answer),
                category=Category(value=row.category),
            ),
            source_updated_at=row.updated_at,
        )

    async def _apply(self, plan: SyncPlan) -> None:
        for external_id in plan.to_delete:
            existing = await self._catalog_command.read_by_id(external_id)
            if existing is None:
                continue
            existing.mark_removed()
            await self._catalog_command.delete_by_id(external_id)

        for pair in plan.to_create:
            created = self._qa_pair_factory.create(
                external_id=pair.external_id,
                content=pair.content,
                source_updated_at=pair.source_updated_at,
            )
            await self._catalog_command.add(created)

        for pair in plan.to_update:
            existing = await self._catalog_command.read_by_id(pair.external_id)
            if existing is None:
                continue
            existing.update_content(
                content=pair.content,
                source_updated_at=pair.source_updated_at,
            )
            await self._catalog_command.update(existing)
