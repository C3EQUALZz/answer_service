from abc import abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol


class SourceFactory(Protocol):
    """Builds a configured ``dature`` source on demand.

    Encapsulates everything source-specific (which backend, prefixes, the
    field-name mapping). A loader depends only on this protocol, so switching
    from env vars to YAML/TOML/Vault is a matter of injecting a different
    factory — the loader code stays untouched.
    """

    @abstractmethod
    def create(self) -> SourceProtocol:
        """Return a ready-to-use source."""
        ...
