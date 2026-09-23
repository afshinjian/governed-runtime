"""GR-17: validation execution may not take egress the activation never granted.

F02-001: `execute_validation` built the executor with no authority check, so a
catalog operation declaring `network="ANY"` reached `--share-net` ungated. The
catalog declares what an operation needs; only the activated contract can grant
it. These tests ask whether authority was checked, not whether the sandbox
still works: the operations here would execute happily without the gate.
"""
import json

import pytest

from gruntime.controller import Controller
from gruntime.errors import CapabilityDenied, PolicyDenied
from gruntime.models import EpistemicClass

from gr06_support import provision
from test_gr09_validation import bind, operation, runtime  # noqa: F401  (fixture)

EGRESS = {'ANY': 'net.egress.any', 'ALLOWLIST': 'net.egress.allowlist'}


def egress_operation(network, **changes):
    """A declared-egress operation: the catalog forces EXTERNAL side effects."""
    return operation(network=network, side_effect_class='EXTERNAL', **changes)


def granted_run(c, project, capability):
    """A second run whose activation actually grants `capability`."""
    run = Controller.open_run(c, project)  # unpatched: no legacy provisioning
    # `proc.exec.validation` is what rows 7.1-2/7.1-3 declare and what
    # `execute_validation` proves (GR-31 C8). This run is the one that reaches
    # the executor, so it legitimately needs it; the refusal tests above use
    # the legacy run and still deny on the egress capability alone.
    provision(c, run, capability_request=['fs.read', 'fs.write', 'commit.propose',
                                          'proc.exec.validation', capability],
              policy_grantable=(capability,))
    return run


def denials(c, project):
    return [json.loads(c.store.artifact_bytes(event.payload_digest))
            for event in c.store.list_events(project) if event.event_type == 'authority.denied']


@pytest.mark.parametrize('network', ['ANY', 'ALLOWLIST'])
def test_declared_egress_without_a_grant_never_reaches_the_executor(runtime, network):
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run, egress_operation(network))
        assert EGRESS[network] not in c.store.activation_for_run(run).granted_capabilities
        with pytest.raises(CapabilityDenied):
            c.execute_validation(run, 'check')
        # No attempt exists, so nothing executed and recovery has nothing to
        # reconcile: the refusal precedes the validation.executing transition.
        assert not c._validation_attempts(project)
        assert [d['capability'] for d in denials(c, project)] == [EGRESS[network]]
        c.store.verify_chain(project)


def test_no_declared_egress_is_checked_for_no_egress_capability(runtime):
    """NONE maps to no capability, so a confined validation stays ungated."""
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run)
        assert c.execute_validation(run, 'check').verdict == 'PASS'
        assert not denials(c, project)


def test_granted_egress_authority_admits_the_operation(runtime):
    """A real grant passes the gate: this is an authority check, not a ban."""
    h, project, _, _, _ = runtime
    with h.controller() as c:
        run = granted_run(c, project, 'net.egress.allowlist')
        assert 'net.egress.allowlist' in c.store.activation_for_run(run).granted_capabilities
        bind(c, run, egress_operation('ALLOWLIST'))
        # Past the gate; the executor then refuses for want of an enforcing
        # adapter (GR-09), which is a different refusal at a different layer.
        receipt = c.execute_validation(run, 'check')
        assert (receipt.verdict, receipt.exit_code) == ('ERROR', None)
        assert b'ALLOWLIST' in c.artifacts.get(receipt.stderr_ref.digest)
        assert not denials(c, project)
        assert c._validation_attempts(project)[receipt.op_id]['status'] == 'EXEC_FAILED'


def test_a_revoked_contract_stops_further_egress_validation(runtime):
    h, project, _, _, _ = runtime
    with h.controller() as c:
        run = granted_run(c, project, 'net.egress.allowlist')
        bind(c, run, egress_operation('ALLOWLIST'))
        c.revoke_contract(c.store.activation_for_run(run).contract_id)
        with pytest.raises(CapabilityDenied):
            c.execute_validation(run, 'check')
        assert not c._validation_attempts(project)


def test_retry_reaches_execution_only_through_the_gated_path(runtime):
    """Retry re-enters execute_validation (validation_controller.py:153).

    It adds no execution path of its own, and an operation declaring egress is
    EXTERNAL by the catalog's consistency rule, which recovery never permits to
    rerun. So retry is refused before the gate rather than around it.
    """
    h, project, run, _, _ = runtime
    with h.controller() as c:
        bind(c, run, egress_operation('ANY'))
        # An adversarial durable record: an interrupted egress attempt that a
        # reconciler wrongly cancelled. Retry must still consult the catalog.
        c._append(project, event_type='validation.executing', epistemic_class=EpistemicClass.AUTHORITY,
                  subject={'run_id': run, 'op_id': 'egress'},
                  payload={'op_id': 'egress', 'run_id': run, 'spec_id': 'check', 'controller_epoch': 0},
                  capability_used='validation.execute')
        c._append(project, event_type='validation.recovered', epistemic_class=EpistemicClass.AUTHORITY,
                  subject={'run_id': run, 'op_id': 'egress'},
                  payload={'op_id': 'egress', 'status': 'CANCELLED'},
                  capability_used='recovery.reconcile')
        with pytest.raises(PolicyDenied, match='recovery forbids'):
            c.retry_validation(run, 'egress')
        assert len(c._validation_attempts(project)) == 1
