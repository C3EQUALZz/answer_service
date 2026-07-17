from dataclasses import dataclass

from sqlalchemy import URL


@dataclass(slots=True, frozen=True)
class PostgresConfig:
    """Configuration container for PostgreSQL database connection settings.

    Plain stdlib dataclass with no dependency on the config loader: all
    dature-specific wiring (env mapping, validation) lives in
    ``answer_service.setup.bootstrap.loaders.postgres_config_loader``.

    Attributes:
        user: Database username.
        password: Database password.
        host: Database server hostname or IP address.
        port: Database server port.
        db_name: Name of the database to connect to.
        driver: Database driver (e.g. ``asyncpg``).

    Properties:
        uri: Complete PostgreSQL connection URI in SQLAlchemy format.
    """

    user: str
    password: str
    host: str
    port: int
    db_name: str
    driver: str

    @property
    def uri(self) -> str:
        """Generates a PostgreSQL connection URI.

        Returns:
            str: Connection string in format:
                postgresql+driver://user:password@host:port/db_name

        Note:
            - Uses the configured driver for async operations.
            - Includes all authentication credentials.
            - Suitable for SQLAlchemy's create_async_engine.
        """
        return URL.create(
            drivername=f"postgresql+{self.driver}",
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.db_name,
        ).render_as_string(hide_password=False)
