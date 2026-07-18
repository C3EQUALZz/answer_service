from pathlib import Path

import pytest

from answer_service.domain.indexing.value_objects.source_reference import SourceReference
from answer_service.infrastructure.adapters.source_file import LocalSourceFileStorage
from answer_service.infrastructure.errors import SourceFileStorageError


async def test_a_saved_file_reads_back_byte_for_byte(
    storage: LocalSourceFileStorage,
) -> None:
    content = b"external_id,question\nq-1,Why?\n"

    reference = await storage.save(content=content, filename="faq.csv")

    assert await storage.open(reference) == content


async def test_the_directory_is_created_on_first_save(
    tmp_path: Path,
    storage: LocalSourceFileStorage,
) -> None:
    """A fresh deployment has no upload directory yet."""
    assert not (tmp_path / "uploads").exists()

    await storage.save(content=b"data", filename="faq.csv")

    assert (tmp_path / "uploads").is_dir()


async def test_two_uploads_of_the_same_name_do_not_collide(
    storage: LocalSourceFileStorage,
) -> None:
    """Two users uploading faq.csv a second apart must not overwrite each other."""
    first = await storage.save(content=b"first", filename="faq.csv")
    second = await storage.save(content=b"second", filename="faq.csv")

    assert first != second
    assert await storage.open(first) == b"first"
    assert await storage.open(second) == b"second"


async def test_the_extension_is_preserved(storage: LocalSourceFileStorage) -> None:
    """Not for parsing — the reader sniffs content — but for readable storage."""
    reference = await storage.save(content=b"data", filename="faq.xlsx")

    assert reference.value.endswith(".xlsx")


async def test_a_file_without_an_extension_is_accepted(
    storage: LocalSourceFileStorage,
) -> None:
    reference = await storage.save(content=b"data", filename="faq")

    assert await storage.open(reference) == b"data"


async def test_reading_a_missing_file_fails_as_a_storage_error(
    storage: LocalSourceFileStorage,
) -> None:
    """The worker may run after the staged file was cleaned up."""
    with pytest.raises(SourceFileStorageError):
        await storage.open(SourceReference(value="/nowhere/at/all.csv"))
