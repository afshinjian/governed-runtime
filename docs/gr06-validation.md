# GR-06 — Stage Contract and Authority Core

The implementation uses `design-01-frozen` unchanged. The packaged StageContract
schema is a byte-for-byte copy, checked by a test. `StageContract` validates the
2020-12 schema with date-time checking, the authoring cross-constraints, NFC and
control-character restrictions. RFC 8785 serialization computes SHA-256 over
every present member except `status` and `contract_hash`. Absent optional
members are not defaulted.

| Requirement | Implementation |
|---|---|
| Contract alone grants nothing | Production `open_run` allocates with no activation and empty effective capabilities. `require_authority` denies it, even if a supplied document says ACTIVE. |
| AX-11 | Register grantors and role eligibility are separate tables. Each grant cites a role default, persisted human decision, or persisted policy evaluation. Ceiling membership is never a grant. |
| Human grants | The immutable decision hash, authentication, kind, capability, project, subject, scope, time, evidence and decision state are checked. A unique nonce claim binds the decision to one activation and prevents reuse across runs. The source decision remains subject to expiry, staleness and revocation. |
| Policy grants | Evaluations reference a human-authored policy artifact at the project's pinned digest. Only registered policy-grantable capabilities survive, only in AUTONOMOUS mode. |
| Activation persistence | Status, activation, run binding, nonce claims and AUTHORITY event commit atomically. Activation records are immutable and hash-verified on reads. |
| F01-005 / XC-12 | Every legal status change preserves the contract hash pinned to the run. A recomputation mismatch is an integrity violation. |
| INV-07 / XC-13 | Persistence rejects any content change under an existing contract ID, even with a recomputed hash. All content is frozen, including objective, prohibited actions, scope, acceptance criteria, requested authority, validation/review specifications and rollback/budget restrictions. |
| Canonical scope | Component-aware POSIX matching supports `*`, `?`, character classes and recursive `**`. Both lexical and resolved paths must satisfy include-minus-exclude. Traversal, alternate path spellings, symlink escape, nested checkouts and Git submodules (including uninitialized Gitlinks) are refused. |
| GR-10 | Proposal, authorization and application under the repository lease read the stored activation and contract. Source and rename destination paths are checked. The caller's `in_scope` flag cannot authorize a path. Recovery still observes prior effects without initiating a commit. |
| Default deny at exercise | Source grants, current ceiling, mode, policy digest, budget, contract status, expiry and prohibited actions are checked again. HUMAN-class and supervised per-action capabilities also require an exercise-time decision; the effect transition remains responsible for consuming it. Denials emit AUTHORITY events. |

The frozen schema has no separate `non_goals` or `commit_policy` extension
members. Such additions are rejected, rather than accepted as unpinned policy.
Non-goals can be expressed through its objective/prohibited-actions fields;
commit-related requests and restrictions use the existing frozen members.

Physical storage version is 4. Project ceiling/budget/usage and human
grants/revokes/signatures are now persisted; earlier schemas are explicitly
refused through the existing storage-version check. The domain schema version
and existing evidence-hash serialization remain unchanged. Contract hashing
uses `rfc8785`; schema validation uses `jsonschema` with a local date checker.
Both are declared installation dependencies, and the schema is packaged in the
wheel.

The shared legacy test harness explicitly provisions a contract and activation
for tests predating GR-06. Production code has no implicit activation or broad
default grant. Original regression assertions are retained.

`bin/check-gr06-mutations` weakens each marked guard sequentially, requires a
failure in `tests/test_gr06_contract_authority.py`, restores the original source,
and requires the full dedicated suite to pass. Mutant runs stop at the first test failure. Collection errors are not kills. Full
regression runs bracket the mutation batch. Detailed mutant/restoration logs
are retained under `.evidence/gr06/`; the checked inventory is published in
`docs/evidence/gr06-mutations.json`.

Verified result: **810 tests pass**, including all 518 original cases, six
additional storage-refusal cases, and 286 GR-06 cases. All **78 guard mutations
are killed** and each restored GR-06 suite passes. The current guard statements
were fingerprinted again and matched against the retained mutation evidence.
The full-suite output is retained in `.evidence/gr06/full-suite.log`.

A wheel build also passed: its dependency metadata names `jsonschema` and
`rfc8785`, its packaged schema is byte-identical to the frozen source, and an
isolated interpreter imported the contract module and loaded that schema from
the wheel. Package-build evidence is in `.evidence/gr06/package.log`.
