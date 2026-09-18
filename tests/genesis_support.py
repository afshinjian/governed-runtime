"""The human whose approval authorizes project creation.

`∅ → DRAFT` is authorized by a `HumanDecision{kind: APPROVE}` over the project
(`AX-14`), so every `create_project` call names the principal who made it.
Tests that are not about authority use this one; tests that are about it build
their own actor.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gruntime.models import (  # noqa: E402
    ActorKind,
    ActorRef,
    AuthMethod,
    GovernanceMode,
)
from gruntime.controller import CreationResponse  # noqa: E402

#: The mode every test that predates the `SUPERVISED` creation gate ran under.
AUTONOMOUS = GovernanceMode.AUTONOMOUS

#: An authenticated human principal: named, keyed, and not delegated.
OWNER = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="owner@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id="key-owner",
)


#: The options the creation presentation offers. `CREATE` is the approving
#: choice; `DECLINE` is the refusal a human may make instead. `chosen` must be
#: one of them (domain-model.md:696, DESIGN-04 §2.23 row 5).
CREATE = "CREATE"
DECLINE = "DECLINE"


def accepting(*, chosen=CREATE, signature=None):
    """A presenter that answers the observation it is actually shown.

    The default human for tests that are not about the boundary: they look at
    what is presented and answer that, which is the only conforming thing a
    presenter can do.
    """

    def present(observation):
        return CreationResponse(
            snapshot_id=observation.snapshot_id, chosen=chosen, signature=signature
        )

    return present


def create_project(controller, *, then_mode=None, present=None, chosen=CREATE,
                   signature=None, **kwargs):
    """Conforming creation for tests, and the test-only mode construction.

    One place for every test's creation call, so the conforming API is adapted
    once rather than at each of the call sites.

    Production creation is `SUPERVISED` and nothing in the runtime moves a
    project out of it: `project.mode.set` has no legal transition row in the
    frozen matrix (DESIGN-04 §2.23 row 1, §6.1). A test that needs an
    `AUTONOMOUS` project therefore **constructs that state directly**, after a
    conforming creation, by passing `then_mode`. That is a fixture writing a
    row, not a transition: it implies no production `SET_MODE` path and
    records no decision, event or authority for the mode it installs.
    """
    kwargs.setdefault("approved_by", OWNER)
    # `initial_mode` has no production default: the mode a creating act
    # establishes is human-supplied, and the runtime never picks it. Tests
    # that are not about the mode get the conforming one from here, and tests
    # that are about it pass their own.
    kwargs.setdefault("initial_mode", GovernanceMode.SUPERVISED)
    project_id = controller.create_project(
        present=present or accepting(chosen=chosen, signature=signature), **kwargs
    )
    if then_mode is not None:
        force_governance_mode(controller.store, project_id, then_mode)
    return project_id


def force_governance_mode(store, project_id, mode):
    """Test-only: put a project into `mode` with no transition of any kind."""
    project = store.get_project(project_id)
    project.governance_mode = mode
    store.put_project(project)


#: A human who authenticates by signature rather than by session. Under
#: [domain-model.md:710](../design/domain-model.md#L710) their decision is
#: only complete when it carries the signature itself (`DESIGN-04-035`).
SIGNER = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="signer@example.invalid",
    auth_method=AuthMethod.SIGNATURE,
    principal_key_id="key-signer",
)

#: Opaque signature evidence. The runtime stores and binds it; it verifies
#: nothing, and no key infrastructure exists to verify it against.
SIGNATURE = "sig-3f9a2c" * 4


#: A human whose own `ActorRef` already delegates. The runtime acting for them
#: under `AX-16` would stand at delegation depth 3, which no act may reach.
OWNER_OF_OWNER = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="delegate@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id="key-delegate",
    on_behalf_of=OWNER,
)
