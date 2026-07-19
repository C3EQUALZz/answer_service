from abc import abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from answer_service.domain.indexing.value_objects.content_hash import ContentHash
    from answer_service.domain.indexing.value_objects.external_id import ExternalId


@dataclass(frozen=True, slots=True)
class CatalogStatistics:
    """How much content the catalog currently holds."""

    total_pairs: int
    pairs_per_category: Mapping[str, int]

    @property
    def category_count(self) -> int:
        return len(self.pairs_per_category)


@dataclass(frozen=True, slots=True)
class QAPairView:
    """A QA pair as a reader sees it, without the aggregate behind it."""

    external_id: str
    question: str
    answer: str
    category: str


class QACatalogQueryGateway(Protocol):
    """Read-side projections over the QA pair catalog."""

    @abstractmethod
    async def read_views(
        self,
        external_ids: Iterable[ExternalId],
    ) -> Mapping[ExternalId, QAPairView]:
        """Return the text of the given pairs, keyed by identity.

        Search ranks identities and joins the text afterwards, in one query
        rather than one per hit. Ids the catalog no longer holds are simply
        absent: a pair deleted between ranking and reading is dropped from the
        results rather than returned hollow.
        """
        raise NotImplementedError

    @abstractmethod
    async def read_fingerprints(self) -> Mapping[ExternalId, ContentHash]:
        """Return the current ``external_id -> content_hash`` manifest for diffing."""
        raise NotImplementedError

    @abstractmethod
    async def read_statistics(self) -> CatalogStatistics:
        """Return catalog size, overall and per category.

        Counted by the database rather than derived from loaded pairs, so the
        answer costs two aggregate queries regardless of catalog size.
        """
        raise NotImplementedError
