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

from gruntime.models import ActorKind, ActorRef, AuthMethod  # noqa: E402

#: An authenticated human principal: named, keyed, and not delegated.
OWNER = ActorRef(
    actor_kind=ActorKind.HUMAN,
    actor_id="owner@example.invalid",
    auth_method=AuthMethod.SESSION,
    principal_key_id="key-owner",
)
