"""The durable core itself: state store, event log, artifact store, epoch.

Design basis: evidence-model §3.1 (chain construction), §3.2 (append protocol),
§3.3 (verification), domain-model §9.C, P-INV-4.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from gruntime.artifacts import ArtifactStore
from gruntime.canonical import canonical_json, digest_bytes
from gruntime.errors import IntegrityViolation
from gruntime.models import EpistemicClass

from genesis_support import AUTONOMOUS, OWNER, create_project


# --- content-addressed artifact store ------------------------------------

def test_artifact_store_is_content_addressed(tmp_path):
    store = ArtifactStore(tmp_path / "cas")
    ref = store.put(b"hello", media_type="text/plain")

    assert ref.digest == digest_bytes(b"hello")
    assert ref.byte_len == 5
    assert store.get(ref.digest) == b"hello"

    again = store.put(b"hello", media_type="text/plain")
    assert again.digest == ref.digest


def test_artifact_store_detects_a_corrupted_payload(tmp_path):
    store = ArtifactStore(tmp_path / "cas")
    ref = store.put(b"payload", media_type="application/json")
    store.path_for(ref.digest).write_bytes(b"tampered")
    with pytest.raises(IntegrityViolation):
        store.get(ref.digest)


def test_missing_artifact_raises(tmp_path):
    store = ArtifactStore(tmp_path / "cas")
    with pytest.raises(KeyError):
        store.get("sha256:" + "ab" * 32)


# --- canonical form -------------------------------------------------------

def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": [1, 2]}) == b'{"a":[1,2],"b":1}'
    assert canonical_json({"a": None, "z": True}) == b'{"a":null,"z":true}'


def test_canonical_json_orders_by_utf16_code_unit():
    #  RFC 8785 sorts by UTF-16 code unit, so a non-BMP key sorts after U+FFF0.
    out = canonical_json({"\U0001f600": 1, "￰": 2}).decode("utf-8")
    assert out.index("￰") < out.index("\U0001f600")


# --- storage configuration ------------------------------------------------

def test_storage_is_wal_synchronous_full_and_strict(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
    conn = sqlite3.connect(h.db_path)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        assert tables
        for table in tables:
            sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE name=?", (table,)
            ).fetchone()[0]
            assert "STRICT" in sql.upper(), f"{table} is not a STRICT table"
    finally:
        conn.close()

    with h.store() as s:
        assert s.pragma("synchronous") == 2  # FULL
        assert s.get_project(project_id).controller_epoch == 0


# --- hash-chained event log ----------------------------------------------

def test_genesis_event_anchors_the_chain(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
    with h.store() as s:
        events = s.list_events(project_id)
        assert events[0].seq == 0
        assert events[0].prev_event_hash == s.genesis_hash(project_id)
        assert s.get_project(project_id).event_head == events[-1].event_hash
        assert s.get_project(project_id).event_seq == events[-1].seq
        s.verify_chain(project_id)


def test_appends_are_gapless_and_advance_the_head(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
        for epoch in range(3):
            c.start(project_id)

    with h.store() as s:
        events = s.list_events(project_id)
        assert [e.seq for e in events] == list(range(len(events)))
        for previous, current in zip(events, events[1:]):
            assert current.prev_event_hash == previous.event_hash
        assert s.get_project(project_id).event_head == events[-1].event_hash
        s.verify_chain(project_id)


def test_every_event_binds_its_payload(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
        c.start(project_id)
    with h.store() as s:
        for event in s.list_events(project_id):
            assert event.payload_digest == event.payload_ref.digest
            assert digest_bytes(s.artifact_bytes(event.payload_digest)) == (
                event.payload_digest
            )
            assert event.epistemic_class in set(EpistemicClass)


def test_verification_detects_a_rewritten_event(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
        c.start(project_id)

    conn = sqlite3.connect(h.db_path)
    try:
        conn.execute(
            "UPDATE audit_events SET event_type='forged' WHERE seq=1 AND project_id=?",
            (project_id,),
        )
        conn.commit()
    finally:
        conn.close()

    with h.store() as s:
        with pytest.raises(IntegrityViolation):
            s.verify_chain(project_id)


def test_verification_detects_a_broken_link(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
        c.start(project_id)
        c.start(project_id)

    conn = sqlite3.connect(h.db_path)
    try:
        conn.execute(
            "DELETE FROM audit_events WHERE seq=1 AND project_id=?", (project_id,)
        )
        conn.commit()
    finally:
        conn.close()

    with h.store() as s:
        with pytest.raises(IntegrityViolation):
            s.verify_chain(project_id)


def test_the_event_log_is_append_only(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
    with h.store() as s:
        with pytest.raises(sqlite3.DatabaseError):
            s.raw_execute(
                "UPDATE audit_events SET event_type='x' WHERE project_id=?",
                (project_id,),
            )
        with pytest.raises(sqlite3.DatabaseError):
            s.raw_execute(
                "DELETE FROM audit_events WHERE project_id=?", (project_id,)
            )


# --- controller_epoch -----------------------------------------------------

def test_epoch_increments_once_per_controller_start(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
        assert c.start(project_id) == 1
        assert c.start(project_id) == 2
    with h.store() as s:
        assert s.get_project(project_id).controller_epoch == 2


def test_operations_carry_the_epoch_they_were_created_under(h):
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
        c.start(project_id)
        run_id = c.open_run(project_id)
        first = c.create_invocation(run_id, prompt=b"one")
    with h.store() as s:
        assert s.get_invocation(first.invocation_id).controller_epoch == 1

    with h.controller() as c:
        assert c.start(project_id) == 2
        c.recover(project_id)
        second = c.create_invocation(run_id, prompt=b"two")
    with h.store() as s:
        assert s.get_invocation(first.invocation_id).controller_epoch == 1
        assert s.get_invocation(second.invocation_id).controller_epoch == 2


def test_the_epoch_bump_is_durable_before_any_work(h):
    """P-INV-4: the increment is committed before the controller does anything."""
    with h.controller() as c:
        project_id = create_project(c, then_mode=AUTONOMOUS, name="core", slug="core",
                                      workspace_root=str(h.root),
                                      approved_by=OWNER)
    proc = h.spawn(project_id, "start")
    out, err = proc.communicate(timeout=60)
    assert proc.returncode == 0, err
    assert json.loads(out)["controller_epoch"] == 1
    with h.store() as s:
        assert s.get_project(project_id).controller_epoch == 1
        s.verify_chain(project_id)
