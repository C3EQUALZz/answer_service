import pytest

from answer_service.domain.indexing.errors import DuplicateExternalIdError
from answer_service.domain.indexing.services.sync_planner import SyncPlanner
from answer_service.domain.indexing.value_objects.external_id import ExternalId
from tests.unit.factories.domain_factories import make_desired_pair, make_manifest
from tests.unit.support import external_ids


def test_an_empty_catalog_means_everything_is_created(planner: SyncPlanner) -> None:
    plan = planner.plan(
        desired=[make_desired_pair("q-1"), make_desired_pair("q-2")], current={}
    )

    assert external_ids(plan.to_create) == ["q-1", "q-2"]
    assert plan.to_update == ()
    assert plan.to_delete == ()
    assert plan.stats().created == 2


def test_an_unchanged_pair_is_skipped(planner: SyncPlanner) -> None:
    """Fingerprint equality is what makes re-running a file free."""
    pair = make_desired_pair("q-1")

    plan = planner.plan(desired=[pair], current=make_manifest(pair))

    assert plan.to_create == ()
    assert plan.to_update == ()
    assert plan.skipped == (ExternalId(value="q-1"),)
    assert plan.stats().skipped == 1


def test_a_changed_pair_is_updated(planner: SyncPlanner) -> None:
    plan = planner.plan(
        desired=[make_desired_pair("q-1", answer="new")],
        current=make_manifest(make_desired_pair("q-1", answer="old")),
    )

    assert external_ids(plan.to_update) == ["q-1"]
    assert plan.to_create == ()


def test_a_pair_missing_from_the_source_is_deleted(planner: SyncPlanner) -> None:
    """Deletion is the set difference — the file is the source of truth."""
    plan = planner.plan(desired=[], current=make_manifest(make_desired_pair("q-gone")))

    assert plan.to_delete == (ExternalId(value="q-gone"),)
    assert plan.stats().deleted == 1


def test_all_four_outcomes_in_one_run(planner: SyncPlanner) -> None:
    plan = planner.plan(
        desired=[
            make_desired_pair("q-new"),
            make_desired_pair("q-same"),
            make_desired_pair("q-changed", answer="new"),
        ],
        current=make_manifest(
            make_desired_pair("q-same"),
            make_desired_pair("q-changed", answer="old"),
            make_desired_pair("q-gone"),
        ),
    )

    assert external_ids(plan.to_create) == ["q-new"]
    assert external_ids(plan.to_update) == ["q-changed"]
    assert plan.to_delete == (ExternalId(value="q-gone"),)
    assert plan.skipped == (ExternalId(value="q-same"),)

    stats = plan.stats()
    assert (stats.created, stats.updated, stats.deleted, stats.skipped) == (1, 1, 1, 1)
    assert stats.total == 4


def test_a_duplicated_external_id_aborts_the_plan(planner: SyncPlanner) -> None:
    """Two rows claiming one id make the outcome depend on ordering."""
    with pytest.raises(DuplicateExternalIdError, match="q-1"):
        planner.plan(
            desired=[make_desired_pair("q-1"), make_desired_pair("q-1", answer="other")],
            current={},
        )


def test_an_empty_source_against_an_empty_catalog_does_nothing(
    planner: SyncPlanner,
) -> None:
    plan = planner.plan(desired=[], current={})

    assert plan.stats().total == 0


def test_planning_does_not_depend_on_manifest_ordering(planner: SyncPlanner) -> None:
    pairs = [make_desired_pair("q-1"), make_desired_pair("q-2"), make_desired_pair("q-3")]
    forward = planner.plan(desired=pairs, current=make_manifest(*pairs))
    backward = planner.plan(desired=pairs, current=make_manifest(*reversed(pairs)))

    assert forward == backward
