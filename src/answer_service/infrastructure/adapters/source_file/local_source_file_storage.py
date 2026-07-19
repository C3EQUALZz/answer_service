import asyncio
import logging
from pathlib import Path
from typing import Final, final, override
from uuid import uuid4

from answer_service.application.common.ports.source_file.source_file_storage import (
    SourceFileStorage,
)
from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.infrastructure.errors import SourceFileStorageError
from answer_service.setup.configs.storage_config import StorageConfig

logger: Final[logging.Logger] = logging.getLogger(__name__)


@final
class LocalSourceFileStorage(SourceFileStorage):
    """Stages uploads on a shared filesystem.

    Files are stored under a generated name rather than the uploaded one: two
    users uploading ``faq.csv`` a second apart must not overwrite each other's
    pending work, and the original name is not something we control.

    Blocking file I/O runs in a thread so it cannot stall the event loop while a
    large upload is written.
    """

    def __init__(self, config: StorageConfig) -> None:
        self._directory: Final[Path] = config.directory

    @override
    async def save(self, *, content: bytes, filename: str) -> SourceReference:
        suffix = Path(filename).suffix
        target = self._directory / f"{uuid4()}{suffix}"

        try:
            await asyncio.to_thread(self._write, target, content)
        except OSError as e:
            logger.exception("source_storage: failed to stage '%s'", filename)
            msg = f"Failed to stage the uploaded file '{filename}'."
            raise SourceFileStorageError(msg) from e

        logger.info(
            "source_storage: staged '%s' as %s (%d bytes)",
            filename,
            target,
            len(content),
        )
        return SourceReference(value=str(target))

    @override
    async def open(self, reference: SourceReference) -> bytes:
        logger.debug("source_storage: opening %s", reference.value)
        try:
            content = await asyncio.to_thread(Path(reference.value).read_bytes)
        except OSError as e:
            logger.exception("source_storage: failed to read %s", reference.value)
            msg = f"Failed to read the staged file '{reference.value}'."
            raise SourceFileStorageError(msg) from e

        logger.debug(
            "source_storage: read %d bytes from %s",
            len(content),
            reference.value,
        )
        return content

    def _write(self, target: Path, content: bytes) -> None:
        self._directory.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
