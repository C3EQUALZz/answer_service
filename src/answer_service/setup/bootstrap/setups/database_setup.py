from answer_service.infrastructure.persistence.models import (
    map_indexing_tasks_table,
    map_outbox_table,
    map_qa_pairs_table,
    map_query_logs_table,
)


def setup_map_tables() -> None:
    """Ensures imperative SQLAlchemy mappings are initialized at application startup.

    ### Purpose:
    In Clean Architecture, domain entities remain agnostic of database
    mappings. To integrate with SQLAlchemy, mappings must be explicitly
    triggered to link ORM attributes to domain classes. Without this setup,
    attempts to interact with unmapped entities in database operations
    will lead to runtime errors.

    ### Solution:
    This function provides a single entry point to initialize the mapping
    of domain entities to database tables. By calling the `setup_map_tables` function,
    ORM attributes are linked to domain classes without altering domain code
    or introducing infrastructure concerns.

    ### Usage:
    Call the `setup_map_tables` function in the application factory to initialize
    mappings at startup. Additionally, it is necessary to call this function
    in `env.py` for Alembic migrations to ensure all models are available
    during database migrations.

    Call exactly once per process. ``map_imperatively`` raises on a class that
    is already mapped, so a second call is a programming error rather than a
    no-op — each entry point invokes it once, and alembic's ``env.py`` runs in a
    process of its own.
    """
    map_qa_pairs_table()
    map_indexing_tasks_table()
    map_outbox_table()
    map_query_logs_table()
