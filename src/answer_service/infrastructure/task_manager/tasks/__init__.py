from .indexing_tasks import setup_indexing_tasks
from .lifecycle_tasks import setup_lifecycle_tasks
from .outbox_tasks import setup_outbox_tasks
from .projection_tasks import setup_projection_tasks

__all__ = [
    "setup_indexing_tasks",
    "setup_lifecycle_tasks",
    "setup_outbox_tasks",
    "setup_projection_tasks",
]
