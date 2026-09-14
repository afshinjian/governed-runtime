# GR-07: worker provider layer

Design basis: `design-01-frozen`, `design/worker_provider.md`, and MICRO-01
decisions D1–D5. The frozen files are unchanged. `DISPATCHING` adds the explicit
durable launch intent requested for GR-07; it is nonterminal and uses the same
reconciliation derivation as every other invocation state.

| Boundary | Implementation |
|---|---|
| Authority | Controller reads the ACTIVE contract and its activation, replays GR-06 grant sources, pins role, capabilities, budget, scope, binding and deadline in the content-addressed request. |
| Observation | Creation, dispatch and bridge calls apply the GR-03 completeness and suspension gates. Only snapshot-bound, in-scope file bytes enter the materialized view. |
| Untrusted repository | File content is an explicitly labelled data collection. It is never parsed as grants, contract overrides, tools, commands or provider selection. |
| Launch | Invocation and lease are committed as `DISPATCHING` before transport execution. The provider separately reserves the idempotency key durably before transport execution. |
| Worker effects | The bridge checks the per-invocation grant, tool surface, lease, current authority and both rename paths. Writes and commits are proposals; no bridge operation commits, pushes or changes the roadmap. |
| CLI output | A strict JSON schema rejects unknown fields, duplicate members, mismatched identities and inconsistent status/reason pairs. Neither adapter searches CLI prose for state. |
| Recovery | Registry lookup selects the originally pinned provider. `lookup(key)` reads its journal and returns ABSENT, LIVE or FINISHED; expired ambiguous reservations report UNAVAILABLE. Recovery never invokes a transport. |
| Reviews | Controller checks fresh session, separate author/reviewer roles, distinct provider and context provenance. `record_worker_review` requires a completed receipt containing the typed verdict. Attestation checks the stored review, receipt provenance and activated contract quorum again (D5). |
| Receipts | Receipt, terminal invocation and audit event persist atomically. Claims, proposed mutations and attempted violations survive reload. Duration and tool counts are measured by the controller. |

The journal retains outcomes without garbage collection, including beyond the
deadline plus recovery window. A reservation without a terminal outcome is
never turned into ABSENT. While its lease is live, recovery tracks it; after
expiry, recovery escalates ambiguity and blocks replacement dispatch.
Cancellation requests are durable and polled by the transport. Leases are
fenced by controller epoch; an old controller cannot mint a direct receipt
after a new controller starts. The new controller adopts the outcome by lookup.

## Adapter use

```python
from gruntime.adapters.claude_code import ClaudeCodeProvider
from gruntime.adapters.codex import CodexProvider
from gruntime.adapters.worker_process import ProcessTransport

provider = CodexProvider(
    governance_directory / "providers",
    transport=ProcessTransport("/usr/bin/codex"),
    read_artifact=controller.store.artifact_bytes,
)
controller.register_provider(provider)
invocation = controller.create_invocation(
    activated_run_id, prompt=b"Implement the contracted change",
    provider_id=provider.provider_id,
)
receipt = controller.invoke(invocation.invocation_id)
```

`ProcessTransport` is a Linux bubblewrap transport with an empty home, cleared
environment, bounded output and process-group termination. It mounts no live
repository or credentials and permits no network. Missing bubblewrap produces
an error receipt. This transport supports offline workers and conformance tests;
live hosted inference requires an operator-supplied broker transport implementing
`run(argv, payload, timeout=..., max_output_bytes=..., cancelled=...)`. That broker
is part of the trusted kernel boundary: it must constrain inference egress and
route worker tools through the bridge. No unsandboxed fallback is shipped.
Token and monetary usage remain unmetered (zero); provider claims are not used
as authoritative billing measurements.

The CLI interfaces were checked against installed `codex exec --help` and
`claude --help`, and the official
[Codex non-interactive documentation](https://developers.openai.com/codex/noninteractive)
and [Claude Code headless documentation](https://code.claude.com/docs/en/headless).
The adapters consume Codex JSON events and Claude's `structured_output` envelope.

Storage layout is v5 because receipts now retain structured details. Older
layouts are refused using the existing structural version check; there is no
pre-release migration. The domain schema and audit genesis version remain 0.1.0.

## Reproduction

```sh
.venv/bin/pytest -q
.venv/bin/python bin/check-gr07-mutations
```

Tests use injectable deterministic transports and real isolated subprocesses;
they make no model API calls. The mutation checker weakens each marked GR-07
guard, requires a test failure, restores the original source, and requires the
same tests to pass. Collection errors are rejected as invalid mutants.
Detailed results are written under `.evidence/gr07/`; the checked-in manifest
is `docs/evidence/gr07-mutations.json`.

| Check | Result |
|---|---|
| Original regression baseline | 936 passed |
| GR-07 tests | 119 cases, including both adapters, injected hostile output and real subprocess containment |
| Complete regression suite | 1,056 passed (all original tests retained) |
| Mutation checks | 98/98 guards killed; every selected test suite passed after restoration |
| Final guard audit | Every manifest fingerprint matches its current source guard |
| Frozen design | No changes |
