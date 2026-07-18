import pytest

from answer_service.domain.indexing.services.sync_planner import SyncPlanner
from answer_service.domain.search.services.rrf_fusion import RrfFusion


@pytest.fixture()
def planner() -> SyncPlanner:
    return SyncPlanner()


@pytest.fixture()
def fusion() -> RrfFusion:
    return RrfFusion()
