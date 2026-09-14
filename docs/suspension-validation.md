# Suspension evidence closure

Choice **(a)**: every escalation declaring a non-`NONE` `suspension_applied`
applies that value. The controller persists the escalation, project suspension,
and AUTHORITY events in one transaction. A run-targeted escalation also suspends
the run and audits that write separately. The existing project gate then bars
new invocations, validations and commits. Lifecycle values are preserved.

The shared application path covers drift, commit integrity and ambiguity,
worker recovery ambiguity, and empty-capability activation. It replaces the
separate drift and commit suspension writes. An escalation declaring `NONE`
has `suspension_target = NONE` and leaves any existing suspension intact.

| Reference rule | Enforcement |
|---|---|
| Non-`NONE` requires a nonempty `suspension_ref` | Controller transition; store insert, whole-row update, targeted update and read |
| `NONE` requires `suspension_ref = None` | The same boundaries, including an otherwise redundant transition |
| Another escalation sets the same suspension value | Update the reference to the new escalation and audit it |
| Suspension persistence fails | Roll back the escalation, state changes and audit events, including inside an existing transaction |

The domain schema and storage version are unchanged. The GR-09 validation gate
test now obtains its suspension through an escalation so its fixture satisfies
the reference invariant. Its denial assertions and all other existing
regression assertions remain in place.

`tests/test_suspension_evidence.py` checks every escalation trigger, every
non-`NONE` suspension value, durable state through a separate connection, audit
references, unchanged lifecycle values, worker recovery, repeated suspension,
both directions of the reference invariant, and transaction rollback on SQLite
write failures. The existing empty-activation test also checks the applied
project and run suspension and the escalation reference.

Verified: the baseline passed all **810 existing tests**. The final suite passes
**936 tests**, including 126 new suspension cases. `bin/mutate` removed each
guard below, ran the full suite, restored the exact original source, and ran the
full suite again. Collection errors do not count as kills.

| Removed guard | Mutant result | Restored result |
|---|---|---|
| Shared escalation suspension application | 56 failed, 880 passed | 936 passed |
| `suspension_ref` iff validation | 81 failed, 855 passed | 936 passed |

Both mutations were killed. The reference mutation fails tests for missing
references on non-`NONE` states and stale references on `NONE`, across every
guarded boundary. The [mutation inventory](evidence/suspension-mutations.json)
retains the exact removed statements, source and guard hashes, summaries and
full log paths. Each entry can be replayed as `bin/mutate <file> <removed>` using
its structured fields. Baseline and focused logs are under
`.evidence/suspension/`.
