"""GR-03 — a database this build cannot read is refused by name.

FIX-3: `StateStore.open()` checks the persisted schema and refuses a stale one
       instead of opening cleanly and failing later with an `IndexError` from
       the row factory.

There is no `ALTER TABLE` migration while `STORAGE_VERSION` is pre-release. The
contract is only that the *first* error an operator sees names the cause: which
storage version the database is, which column is missing, and that no migration
exists.

`STORAGE_VERSION` (`PRAGMA user_version`) is deliberately not `SCHEMA_VERSION`.
The latter is the domain-model version (domain-model §2) and anchors every
chain's genesis hash; the frozen model did not change in GR-03, so it must not
move for a storage-only reason.

The legacy shape is reproduced the way it actually occurs — `CREATE TABLE IF
NOT EXISTS` is a no-op on an existing table, so a GR-01/GR-02 database keeps
its old columns and the new code reads straight past them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gruntime.errors import SchemaTooOld
from gruntime.store import (
    REQUIRED_COLUMNS,
    SCHEMA_VERSION,
    STORAGE_VERSION,
    StateStore,
)

#: What `PRAGMA user_version` reads as on a database that never set it.
UNSTAMPED = 0


def _drop_column(db_path: Path, table: str, column: str) -> None:
    """Reshape a database into the one an older build left behind.

    The storage stamp is cleared too: an older build never set it, so a test
    fixture that kept it would be a database no version of the code produces.
    """
    store = StateStore.open(db_path)
    store.raw_execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    store.raw_execute(f"PRAGMA user_version={UNSTAMPED}")
    store.close()


def _legacy_database(h, *, table: str, column: str) -> None:
    """A populated database in the shape GR-01/GR-02 left behind."""
    with h.controller() as controller:
        controller.create_project(
            name="Legacy", slug="legacy", workspace_root=str(h.root)
        )
    _drop_column(h.db_path, table, column)


# --- the refusal ------------------------------------------------------------


def test_a_stale_database_is_refused_by_version_and_column(h):
    _legacy_database(h, table="projects", column="suspension_ref")

    with pytest.raises(SchemaTooOld) as refusal:
        StateStore.open(h.db_path)

    message = str(refusal.value)
    assert f"storage version {UNSTAMPED}" in message, (
        "the refusal does not say which storage version the database is"
    )
    assert f"storage version {STORAGE_VERSION}" in message, (
        "the refusal does not say which storage version this build wants"
    )
    assert SCHEMA_VERSION in message, "the refusal does not say which domain model"
    assert "projects.suspension_ref" in message, "the refusal does not name the column"
    assert "no migration path" in message


def test_the_snapshot_drift_columns_are_checked_too(h):
    _legacy_database(h, table="snapshots", column="drift_summary")
    with pytest.raises(SchemaTooOld) as refusal:
        StateStore.open(h.db_path)
    assert "snapshots.drift_summary" in str(refusal.value)


@pytest.mark.parametrize(
    ("table", "column"),
    [(table, column) for table, columns in REQUIRED_COLUMNS for column in columns],
)
def test_every_column_the_build_added_is_covered(h, table, column):
    """The check is exhaustive over `REQUIRED_COLUMNS`, not a sample of it."""
    db_path = h.root / f"{table}-{column}.db"
    _drop_column(db_path, table, column)
    with pytest.raises(SchemaTooOld) as refusal:
        StateStore.open(db_path)
    assert f"{table}.{column}" in str(refusal.value)


def test_a_database_with_no_project_row_is_still_refused(h):
    """It cannot name its domain model, so the refusal says so and goes on."""
    _drop_column(h.db_path, "projects", "suspension_ref")
    with pytest.raises(SchemaTooOld) as refusal:
        StateStore.open(h.db_path)
    message = str(refusal.value)
    assert "unknown" in message
    assert "projects.suspension_ref" in message


def test_a_refused_open_leaves_no_connection_behind(h):
    """Refusing twice gives the same answer, not a lock or a stale handle."""
    _legacy_database(h, table="projects", column="suspension_ref")
    messages = []
    for _ in range(2):
        with pytest.raises(SchemaTooOld) as refusal:
            StateStore.open(h.db_path)
        messages.append(str(refusal.value))
    assert messages[0] == messages[1]


# --- the schema this build writes ------------------------------------------


def test_a_fresh_database_is_never_refused(h):
    """The check must not fire on the schema this build itself writes."""
    StateStore.open(h.db_path).close()
    StateStore.open(h.db_path).close()


def test_a_populated_current_database_reads_back(h):
    """The columns the check insists on are the ones a read actually needs."""
    with h.controller() as controller:
        project_id = controller.create_project(
            name="Current", slug="current", workspace_root=str(h.root)
        )
    store = StateStore.open(h.db_path)
    try:
        project = store.get_project(project_id)
        assert project.schema_version == SCHEMA_VERSION
        assert project.suspension_ref is None
    finally:
        store.close()


def test_a_current_database_is_stamped_with_the_storage_version(h):
    """The version travels with the file, not re-derived from columns."""
    store = StateStore.open(h.db_path)
    try:
        assert store.storage_version() == STORAGE_VERSION
    finally:
        store.close()


def test_the_storage_version_is_not_the_domain_model_version(h):
    """`design-01-frozen` did not change; a storage bump must not claim it did.

    `SCHEMA_VERSION` anchors `genesis_hash` (evidence-model §3.1 step 5), so
    tying it to the physical layout would re-anchor every new project's chain
    whenever a column was added.
    """
    with h.controller() as controller:
        project_id = controller.create_project(
            name="Anchor", slug="anchor", workspace_root=str(h.root)
        )
    store = StateStore.open(h.db_path)
    try:
        assert SCHEMA_VERSION == "0.1.0", "the frozen domain model version moved"
        assert store.storage_version() == STORAGE_VERSION
        events = store.list_events(project_id)
        assert events[0].prev_event_hash == store.genesis_hash(project_id)
    finally:
        store.close()
