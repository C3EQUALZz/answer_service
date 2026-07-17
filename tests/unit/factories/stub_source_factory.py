from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast, override

from dature import EnvSource

from answer_service.setup.bootstrap.sources.source_factory import SourceFactory

if TYPE_CHECKING:
    from dature.sources.protocol import SourceProtocol
    from dature.type_aliases import FieldMapping, JSONValue


@dataclass(kw_only=True, repr=False)
class DictSource(EnvSource):
    """A dature source that serves values straight from a dict.

    Reuses ``EnvSource``'s field mapping / type conversion, but overrides
    :meth:`_load` to return an in-memory mapping instead of ``os.environ`` — no
    files, no ``.env`` parsing, no environment access.
    """

    data: dict[str, str] = field(default_factory=dict)

    @override
    def _load(self) -> JSONValue:
        return cast("JSONValue", self.data)


class StubSourceFactory(SourceFactory):
    """In-memory :class:`SourceFactory` for tests.

    Implements the production ``SourceFactory`` protocol and serves fixed values
    from a plain dict, so loading is fully deterministic and never touches the
    environment. Use :meth:`mirroring` to reuse a real factory's
    ``field_mapping`` (then ``values`` are keyed by real env var names); omit it
    to key ``values`` directly by field name.
    """

    def __init__(
        self,
        values: dict[str, str],
        field_mapping: FieldMapping | None = None,
    ) -> None:
        self._values = values
        self._field_mapping = field_mapping

    @override
    def create(self) -> SourceProtocol:
        return DictSource(data=self._values, field_mapping=self._field_mapping)

    @classmethod
    def mirroring(
        cls,
        factory: SourceFactory,
        values: dict[str, str],
    ) -> StubSourceFactory:
        """Build a stub that reuses ``factory``'s field mapping.

        Args:
            factory: A production factory whose env-name -> field mapping should
                be reused (so ``values`` are keyed by real env var names).
            values: Env-var-name -> value pairs to serve.
        """
        field_mapping = getattr(factory.create(), "field_mapping", None)
        return cls(values=values, field_mapping=field_mapping)
