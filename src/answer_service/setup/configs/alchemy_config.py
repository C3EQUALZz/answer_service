from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SQLAlchemyConfig:
    """Configuration container for SQLAlchemy engine and session settings.

    Plain stdlib dataclass; env mapping and validation live in
    ``answer_service.setup.bootstrap.loaders.alchemy_config_loader``.
    """

    pool_pre_ping: bool
    pool_recycle: int
    pool_size: int
    max_overflow: int
    echo: bool
    auto_flush: bool = False
    expire_on_commit: bool = False
    future: bool = True
