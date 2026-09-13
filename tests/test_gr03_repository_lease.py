"""GR-03 — two controllers cannot hold one repository at once.

Acceptance criteria:
    Two controller instances cannot hold the lease simultaneously. Prove it.
    A stale lease from a dead controller is reclaimable only after expiry.

The proof is not a mock. A real controller subprocess acquires the lease and
blocks inside it at a declared gate point; a second controller, in this
process, is refused. The first is then SIGKILLed — which releases the kernel's
`flock` and leaves the lease record behind — and the second is refused again,
because a lease is honoured until it expires and never because a pid is alive.

Design basis: `gruntime/lease.py`, `CM-INV-2`/`CM-INV-3`, `G-9`.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from gruntime.errors import LeaseUnavailable
from gruntime.lease import LeaseRecord, RepositoryLease, lease_name_for

from gr03_support import project_with_repo

#: Short enough that the expiry test finishes, long enough that the refusal
#: assertions are not racing the clock on a loaded machine.
TTL_MS = 2_500


def _lease(h, holder: str, *, ttl_ms: int = TTL_MS) -> RepositoryLease:
    return RepositoryLease(
        h.root / "leases", h.repo_dir, holder_id=holder, ttl_ms=ttl_ms
    )


# --- the record's own rule --------------------------------------------------


def test_expiry_is_a_question_about_time_and_nothing_else():
    now = datetime.now(timezone.utc)
    record = LeaseRecord(
        lease_id="lease-1",
        holder_id="a",
        repository_root="/nowhere",
        acquired_at=now,
        expires_at=now + timedelta(milliseconds=500),
        pid=1,
    )
    assert record.expired(now) is False
    assert record.expired(now + timedelta(milliseconds=499)) is False
    assert record.expired(now + timedelta(milliseconds=500)) is True


def test_one_repository_yields_one_lease_name(h):
    """Two controllers pointed at the same checkout collide by construction."""
    h.init_repo()
    nested = h.repo_dir / "." / "sub" / ".."
    assert lease_name_for(h.repo_dir) == lease_name_for(nested)
    assert lease_name_for(h.repo_dir) != lease_name_for(h.root)


# --- mutual exclusion in one process ---------------------------------------


def test_a_second_holder_is_refused_while_the_first_holds(h):
    h.init_repo()
    first, second = _lease(h, "first"), _lease(h, "second")
    held = first.acquire()
    with pytest.raises(LeaseUnavailable) as refusal:
        second.acquire()
    assert "first" in str(refusal.value)
    assert second.current().lease_id == held.lease_id, "the refusal took the lease"


def test_the_lease_is_not_reentrant(h):
    """"I already hold it" is a claim about program structure, not the repo."""
    h.init_repo()
    lease = _lease(h, "same-controller")
    lease.acquire()
    with pytest.raises(LeaseUnavailable):
        lease.acquire()


def test_release_hands_the_repository_over(h):
    h.init_repo()
    first, second = _lease(h, "first"), _lease(h, "second")
    first.acquire()
    first.release()
    assert second.acquire().holder_id == "second"


def test_a_released_lease_leaves_no_record(h):
    h.init_repo()
    lease = _lease(h, "first")
    lease.acquire()
    lease.release()
    assert lease.current() is None


def test_releasing_a_reclaimed_lease_does_not_steal_it_back(h):
    """A third controller must not inherit the repository by accident."""
    h.init_repo()
    first = _lease(h, "first", ttl_ms=1)
    second = _lease(h, "second")
    first.acquire()
    time.sleep(0.01)
    reclaimed = second.acquire()
    first.release()
    assert second.current() is not None
    assert second.current().lease_id == reclaimed.lease_id


def test_renewal_extends_the_hold_and_only_for_the_holder(h):
    h.init_repo()
    first, second = _lease(h, "first"), _lease(h, "second")
    original = first.acquire()
    renewed = first.renew()
    assert renewed.lease_id == original.lease_id
    assert renewed.expires_at > original.expires_at
    with pytest.raises(LeaseUnavailable):
        second.renew()


def test_an_expired_lease_is_reclaimed_and_the_reclamation_is_recorded(h):
    h.init_repo()
    first = _lease(h, "first", ttl_ms=1)
    first.acquire()
    time.sleep(0.01)
    reclaimed = _lease(h, "second").acquire()
    assert reclaimed.holder_id == "second"
    assert reclaimed.reclaimed_from == "first", "a broken hold was not recorded"


# --- two real controllers --------------------------------------------------


def test_two_controller_processes_never_hold_the_repository_at_once(h):
    """A live controller inside the lease; a second one refused."""
    project_id = project_with_repo(h, slug="lease")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)

    holder = h.spawn(
        project_id,
        "commit",
        "--run",
        run_id,
        "--path",
        "feature.txt",
        "--content",
        "governed\n",
        gate="inside_repository_lease",
        lease_ttl_ms=TTL_MS,
    )
    try:
        h.wait_for_gate("inside_repository_lease", holder)

        with h.controller(with_repo=True) as second:
            record = second.repository_lease(project_id).current()
            assert record is not None, "the holder did not record its lease"
            assert not record.expired()
            with pytest.raises(LeaseUnavailable):
                second.repository_lease(project_id).acquire()
    finally:
        h.kill9(holder)


def test_a_dead_controllers_lease_is_reclaimable_only_after_it_expires(h):
    project_id = project_with_repo(h, slug="lease-expiry")
    with h.controller(with_repo=True) as controller:
        run_id = controller.open_run(project_id)

    holder = h.spawn(
        project_id,
        "commit",
        "--run",
        run_id,
        "--path",
        "feature.txt",
        "--content",
        "governed\n",
        gate="inside_repository_lease",
        lease_ttl_ms=TTL_MS,
    )
    h.wait_for_gate("inside_repository_lease", holder)
    h.kill9(holder)

    # SIGKILL released the kernel's flock. The lease is a record with an
    # expiry, so the repository stays held anyway.
    with h.controller(with_repo=True) as survivor:
        stale = survivor.repository_lease(project_id).current()
        assert stale is not None
        assert not stale.expired(), "the test raced its own TTL"
        with pytest.raises(LeaseUnavailable) as refusal:
            survivor.repository_lease(project_id).acquire()
        assert "until it expires" in str(refusal.value)

        # Nothing but elapsed time changes the answer.
        while not stale.expired():
            time.sleep(0.05)
        reclaimed = survivor.repository_lease(project_id).acquire()
        assert reclaimed.reclaimed_from == stale.holder_id
        assert reclaimed.holder_id != stale.holder_id
