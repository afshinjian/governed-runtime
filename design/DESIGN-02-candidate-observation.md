# DESIGN-02 — Candidate Observation

| Property | Amendment |
|---|---|
| Baseline | `design-01-frozen`; this document is the amendment, not a replacement of that baseline |
| Gap | `apply_commit` materializes proposals and commits them together. Precommit validation cannot observe proposed contents. |
| Decision | Add `CandidateObservation`, backed by a durable `CandidateMaterialization` operation. Materialize, observe, validate/review, authorize, then commit. |
| Boundary | **The governed worktree is not the user checkout.** Candidate contents live in the runtime-owned governed worktree, outside the user checkout. |
| Scope | One materialization owns a project's governed worktree at a time; one complete, ordered proposal list from one `WorkerReceipt` per candidate. No proposal merging, rebasing, checkout synchronization, or new stage lifecycle. |
| Compatibility | Normative additions and replacements are specified here only. No frozen document, schema file, or implementation is changed by this amendment. |

## 1. Observation target and workspace boundary

| Location | Contents and authority | Observation |
|---|---|---|
| User checkout, resolved from `Project.workspace_root` | Human's files, index, `HEAD`, and branch. Candidate materialization and commit do not write these. | Existing `RealitySnapshot`; continues to populate `Project.snapshot_current` |
| Governed worktree, under the governance directory at `worktrees/<project_id>` | Dedicated checkout of the governed line. Kernel materializes here; later commits the measured contents here. VCS objects may be shared with the user checkout, but its files, index, and checked-out ref are separate. | New `CandidateObservation` while proposed contents are uncommitted; existing commit verification after commit |
| Validation sandbox | Read-only candidate input mounted at its sandbox workspace root; writable output/scratch mounts are separate. No writable alias to the governed tree, its index, or repository metadata. | `ValidationReceipt` over the identified candidate input |
| Artifact store | Candidate manifest, proposal payloads, observations, receipts, and audit records | Durable evidence; a directory's continued existence is not the evidence record |

| Rule | Required behavior |
|---|---|
| Placement | Resolve physical paths before use. Governed and user roots must be distinct, non-nested directories, with no writable file aliases. Refuse a placement that can mutate the user checkout. |
| Scope | `Path` remains workspace-relative; `Glob` remains a glob over those paths. `scope = [Glob]` selects paths **within** an already selected target. Neither `scope` nor `CommandSpec.cwd` selects a host root. |
| Resolution | The kernel resolves an observation ID to its entity and target. For a candidate, follow `materialization_id` to the kernel-owned worktree placement. Callers cannot override that root. Paths such as `src/a.py` have the same logical meaning in both targets. |
| Containment | Preserve include-minus-exclude checks, source and rename-destination checks, protected-path rules, and read grants. Root selection grants no additional filesystem access. Reject unsupported entries or escaping links; a `COMPLETE` manifest cannot silently omit them. |
| W-INV-2 replacement | Worker proposals never write the user workspace. The kernel may materialize their exact contents in the isolated governed worktree before authorization to commit. Only `commit.apply` may turn those contents into a governed revision. |

The frozen sentence “Only an applied `CommitIntent` does” cannot also prohibit
every precommit write in the governed worktree: that would preserve the gap.
This amendment explicitly permits kernel staging there. It does not reinterpret
the user checkout as staging or claim that an uncommitted candidate was applied.

## 2. Separate entity versus extending `RealitySnapshot`

| Choice | Benefit | Consequence |
|---|---|---|
| Add `root` or `target` to `RealitySnapshot` | Reuses its manifest and existing receipt reference type | Every consumer of “newest snapshot,” `snapshot_current`, stage satisfaction, drift, and snapshot-bound decisions must distinguish targets. A host path alone does not bind contents to a receipt, base, or materialization generation; those fields and lifecycle rules are still needed. |
| Separate `CandidateObservation` **(chosen)** | Makes an observation of proposed contents distinct from evidence about the user's current workspace; carries explicit proposal provenance | Validation, review, and commit-decision input references need a bounded union. Candidate currency and operation recovery must be defined explicitly. |

`RealitySnapshot` gains **no root or target field**. Its meaning and ordinary
consumers remain workspace-specific. Reusing its path vocabulary and hashing
rules does not make a candidate a `RealitySnapshot`. In particular,
`RealitySnapshot.trigger = PRE_COMMIT` still observes the user checkout.

## 3. Typed schema delta

DESIGN-01 notation applies: `I` immutable, `M` mutable, `D` derived; all new
fields are supplied or computed by the runtime (`R`). Optional means absent,
not null. Entity schemas are closed: fields not specified here or inherited
from DESIGN-01 are rejected.

| New type | Definition |
|---|---|
| `RuntimePath` | Canonical absolute host filesystem path; kernel configuration/placement only. Distinct from DESIGN-01 `Path`; never a worker-supplied command path. |
| `ObservationRef` | `Ref<RealitySnapshot ∪ CandidateObservation>`: an `Id` resolving to exactly one of these two entity types |
| `MaterializationStatus` | `Enum<PLANNED,MATERIALIZING,READY,DISCARDING,DISCARDED,COMMITTED>`; last two terminal |
| `CandidateFile` | `{path: Path, kind: Enum<REGULAR,SYMLINK>, content_ref: ArtifactRef, mode: uint16}`; a symlink's content is its link text, never dereferenced during measurement |
| `CandidateIndex` | `[CandidateFile]`, sorted by `path`, duplicate-free; absent paths represent nonexistence, so deletes and rename sources are verifiable |
| `CandidateDiscardReason` | `Enum<MATERIALIZATION_FAILED,SUPERSEDED,VALIDATION_FAILED,REVIEW_FAILED,BASE_DRIFT,CONTENT_DRIFT,CONTEXT_DRIFT,CONTRACT_ENDED,RUN_ENDED,CANCELLED>` |

IDs are globally unique across both observation entity types. An unresolved,
ambiguous, wrong-project, or wrong-run reference is an integrity violation.
`ObservationRef` is a referential constraint, not merely JSON Schema `oneOf`
between two indistinguishable string patterns. Existing receipt hashes and
attestations cover the actual `input_snapshot_id`; an ID is never an alias for
“latest,” a directory name, or a tree digest.

### 3.1 `CandidateMaterialization` — durable operation, not acceptance evidence

| Field | Type | Mutability | Constraint |
|---|---|---|---|
| `materialization_id` | `Id` | I | Durable operation identity, allocated before any worktree creation or write |
| `project_id` | `Ref<Project>` | I | Derived through the run |
| `run_id` | `Ref<StageRun>` | I | Owns this operation |
| `worker_receipt_id` | `Ref<WorkerReceipt>` | I | Receipt of an invocation belonging to this run |
| `worker_receipt_hash` | `Hash` | I | Pins the persisted source receipt body |
| `source_snapshot_id` | `Ref<RealitySnapshot>` | I | Exact worker input from persisted `InvocationRequest.scope_view.snapshot_id` |
| `contract_hash` | `Hash` | I | Equals the run's pinned contract hash |
| `proposals_digest` | `Hash` | I | Hash of the canonical ordered `WorkerReceipt.proposed_mutations` list |
| `base_revision_id` | `Str(1..128)` | I | Observed committed head of the governed line before materialization |
| `target_ref` | `Str(1..256)` | I | Governed line; cannot be the ref checked out by the user |
| `expected_file_index_ref` | `ArtifactRef` | I | `CandidateIndex` predicted from the full committed base plus the exact proposal list |
| `expected_tree_digest` | `Hash` | I | Tree digest of that predicted index |
| `worktree_root` | `RuntimePath` | I | Kernel-resolved governed placement, verified against project/repository identity |
| `controller_epoch` | `uint64` | I | Project epoch at allocation |
| `reconciliation_state` | `Enum<NOT_REQUIRED,PENDING,ADOPTED,ORPHANED,UNRESOLVABLE>` | D/M | DESIGN-01's shared derivation, extended to this operation (§7) |
| `status` | `MaterializationStatus` | M | Only transitions in §6 and §7 |
| `observation_id` | `Ref<CandidateObservation>?` | I once present | Set only when a complete observation is durably published |
| `discard_reason` | `CandidateDiscardReason?` | I once present | Required on entry to `DISCARDING`; retained in `DISCARDED` |

### 3.2 `CandidateObservation` — immutable OBSERVATION-grade EVIDENCE

| Field | Type | Mutability | Constraint |
|---|---|---|---|
| `observation_id` | `Id` | I | Fresh identity for this measured materialization, even if another candidate has identical bytes |
| `materialization_id` | `Ref<CandidateMaterialization>` | I | Exactly one observation per successfully sealed materialization |
| `project_id` | `Ref<Project>` | I | Equals materialization's project |
| `run_id` | `Ref<StageRun>` | I | Equals materialization's run |
| `worker_receipt_id` | `Ref<WorkerReceipt>` | I | Equals materialization's source receipt |
| `worker_receipt_hash` | `Hash` | I | Equals materialization's pinned source hash |
| `source_snapshot_id` | `Ref<RealitySnapshot>` | I | Equals materialization's worker input snapshot |
| `contract_hash` | `Hash` | I | Equals materialization's pinned contract |
| `proposals_digest` | `Hash` | I | Recomputed from the source receipt; must equal materialization's value |
| `base_revision_id` | `Str(1..128)` | I | Equals materialization's base |
| `target_ref` | `Str(1..256)` | I | Equals materialization's governed line |
| `scope` | `[Glob]` | I | Fixed to `["**"]`, the whole candidate tree; includes dotfiles, excludes repository control metadata |
| `completeness` | `Enum<COMPLETE>` | I | No usable observation is minted on a partial, truncated, or failed walk; operation failure is audited |
| `file_index_ref` | `ArtifactRef` | I | `CandidateIndex` measured from materialized filesystem entries, with digest-verified content artifacts |
| `tree_digest` | `Hash` | I | Measured Merkle root over sorted relative paths, entry kinds, content digests, and modes |
| `toolchain_digest` | `Hash` | I | Runtime-resolved validation toolchain |
| `env_digest` | `Hash` | I | Runtime-resolved allowlisted environment; no secret values |
| `taken_at` | `Ts` | I | Observation completion time |
| `taken_by` | `ActorRef` | I | `actor_kind = RUNTIME` |
| `attribution` | `Enum<DIRECT,RECONCILED>` | I | Normal observation or observation adopted during recovery |
| `observation_hash` | `Hash` | D/I | Hash of JCS of this record excluding only `observation_hash` |

The measured and predicted indexes must agree on every entry, absence, kind,
content, and mode, with the same tree-digest algorithm. Merely hashing
`after_ref` values or reusing the predicted index is not observation. The
kernel reads the actual materialized files after writes complete and before
making the observation available. The evidence event binds its payload through
the existing `AuditEvent` hash chain; this entity is not a receipt and adds no
alternate attestation or log format.

### 3.3 Existing entity additions and reference changes

| Entity.field | New type | Mutability / restriction |
|---|---|---|
| `ValidationOperation.input_snapshot_id` | `ObservationRef` | New, required, I; kernel selects and persists before execution |
| `ValidationReceipt.input_snapshot_id` | `ObservationRef` | Existing field widened; must equal its operation's pinned input |
| `Review.input_snapshot_id` | `ObservationRef` | Existing field widened for candidate reviews |
| `ReviewAttestation.input_snapshot_id` | `ObservationRef` | Existing field widened; all counted reviews must cite the same ID |
| `HumanDecision.subject_snapshot_id` | `ObservationRef?` | Existing field widened; candidate reference permitted only for a `COMMIT_INTENT` subject, whose candidate is the same ID |
| `CommitIntent.candidate_observation_id` | `Ref<CandidateObservation>` | New, required, I for intents created under DESIGN-02 |
| `CommitReceipt.candidate_observation_id` | `Ref<CandidateObservation>` | New, required, I for those intents; copied from intent on direct or reconciled settlement |

All other snapshot references retain their DESIGN-01 types, including
`Project.snapshot_current`, run input/output, activation input,
`CriterionState.evaluated_against_snapshot`, and `CommitReceipt.post_snapshot_id`.
An old intent with no candidate link is not silently eligible for the new
commit path. Deployment/version migration is not specified by this amendment.

## 4. Provenance, validation, and currency

| Invariant | Required check |
|---|---|
| `CO-1`: provenance | Resolve observation → materialization → source receipt → invocation → run and its persisted request. All identities and hashes must agree. No caller-provided proposal list substitutes for the receipt's complete ordered list. `DIRECT` and correctly reconciled source receipts are equally attributable. |
| `CO-2`: base | Before writing, verify clean governed index/worktree, `HEAD = base_revision_id`, and `target_ref`. The committed base must match the worker's source snapshot over its supplied read scope, and every proposal preimage must match. Dirty user-only inputs or a changed governed base are not silently imported or rebased; obtain fresh worker input/proposals. |
| `CO-3`: isolation | Persist exclusive worktree ownership by `materialization_id`. Use repository leases for writes and sealing; freeze candidate inputs while they are current. Other runs cannot materialize or commit into the reserved tree. Releasing an OS lock during validation or human review does not release durable ownership. |
| `CO-4`: measured input | At validation start verify a complete candidate and its actual input manifest, toolchain, and environment against the pinned observation. Run the contract's unchanged command with `cwd` resolved within that input. Tests may write only to separate scratch/output mounts; such outputs never enter the candidate. If the input cannot be isolated or changes, produce no qualifying `PASS`. |
| `CO-5`: receipt binding | A candidate validation has `receipt.input_snapshot_id = operation.input_snapshot_id = candidate.observation_id`. The receipt is evidence of executing over those contents, not over the base checkout. Missing candidate evidence cannot fall back to `run.input_snapshot_id` or `Project.snapshot_current`. |
| `CO-6`: commit binding | Intent mutations equal the source receipt's ordered proposals; run, contract, base, target, and expected tree agree with the candidate/materialization. All mandatory validation and review preconditions cite this exact observation ID. Equal tree digests across different candidates are insufficient. |
| `CO-7`: claims | The source `WorkerReceipt` still proves what was proposed; its claims remain claims. The candidate proves what the kernel measured on disk. Only qualifying validation/review receipts prove their respective results. |

| Currency case | Rule (V-INV-2 and RA-INV-4) |
|---|---|
| Current candidate | Its materialization is `READY`, owns the worktree, is reconciled if necessary, and has not been invalidated. Source workspace evidence is still current over the relevant scope; the governed base/ref, measured contents, pinned contract, toolchain, and environment still match. Recheck at execution, authorization, and immediately before commit. |
| Superseded | Rework or a replacement materialization invalidates the old candidate and its receipts, even if replacement bytes match. The controller records discard/invalidation before making another candidate current. |
| Drift | A source snapshot superseded within scope, changed governed base/ref, candidate content change, or changed execution context ends currency. A changed candidate is never edited in place under its old ID. |
| Receipt after invalidation | Retain the actual result as historical evidence, but it cannot discharge a current precondition. Staleness is not a rewritten `FAIL`. |
| Commit/discard | `COMMITTED`, `DISCARDING`, or `DISCARDED` ends eligibility for new candidate-based actions. Receipts remain evidence of the already performed validation and authorization. |
| Replay | Candidate deterministic replay keys additionally bind `observation_hash` to the frozen contract/spec/tree/toolchain/environment tuple. A replay hit also requires the same observation ID and current-candidate check. No cross-target or cross-generation receipt reuse. |
| Commit approval | `evidence_shown` includes the candidate manifest/diff and its qualifying receipts. `subject_snapshot_id` equals the intent's candidate ID. Candidate invalidation stales an unconsumed decision; new receipts do not revive it. Consumption and nonce rules remain unchanged. |

V-INV-2 therefore retains its rule: a receipt names the observation it actually
measured, and ceases to be current when that input is superseded in scope. The
amendment adds a separate currency domain for candidates; neither candidate
time nor candidate tree equality can make a workspace receipt current.

| Consumer | Admissible evidence |
|---|---|
| Precommit validation/review and commit authorization | Current `CandidateObservation` and receipts/review attestations bound to that same candidate |
| `Stage.observed_satisfaction`, stage `SATISFIED`, run `CLOSED_SATISFIED` | Existing complete `RealitySnapshot` and workspace-bound evidence rules only |
| Commit settlement | Candidate-bound commit receipt verifies the governed revision; `post_snapshot_id` still identifies an independently taken `RealitySnapshot` of the user checkout |

A successful governed commit does not make the unchanged user checkout satisfy
the stage. There is no automatic promotion, ID rewriting, or reminting of
candidate validation receipts as workspace validation receipts. Workspace
satisfaction requires observation and qualifying validation/review of that
workspace. Synchronizing it with the governed line remains a separate action.

## 5. Split operation and authority

| Operation signature | Responsibility | Boundary |
|---|---|---|
| `materialize_candidate(run_id: Ref<StageRun>, worker_receipt_id: Ref<WorkerReceipt>) -> Ref<CandidateObservation>` | Persist materialization plan/identity; write exact proposals into governed worktree; seal and directly observe contents | Before validation and commit authorization; advances no revision/ref and emits no `CommitReceipt`. Requires an existing governed line; any worktree allocation checks out its pinned base. |
| `commit_candidate(intent_id: Ref<CommitIntent>) -> Ref<CommitReceipt>` | Verify current candidate and authority; commit its already materialized contents and settle receipt | After validation/review and authorization; does not apply proposals again or run a formatter/fixer |

The first operation replaces the materializing part of `apply_commit`; the
second replaces its committing part. No combined entry point may bypass the
observable `READY` interval or its evidence gates. Create the `CommitIntent`
after candidate receipts exist, so `preconditions` stays immutable. The final
supervised approval is subsequently recorded for the authorization transition,
not patched into that immutable precondition set.

| CapabilityId | Permits | Class | Grantable by | Default | Mode rule |
|---|---|---|---|---|---|
| `candidate.materialize` (new) | Plan, write, reserve, invalidate, and clean up candidate staging; no revision creation | `KERNEL` | `RUNTIME_KERNEL` | `DENY` | `AUTO` in both modes, subject to contract scope/write authority and effect gates |
| `snapshot.take` (extended) | Mint direct `CandidateObservation` as well as `RealitySnapshot` | `KERNEL` | `RUNTIME_KERNEL` | `DENY` | `AUTO` |
| `commit.apply` (narrowed forward path) | Commit the authorized, already measured candidate on the governed line; existing rollback authority retained | `KERNEL` | `RUNTIME_KERNEL` | `DENY` | `AUTO`; authorization still precedes commit |
| `recovery.reconcile` (extended subject set) | Observe/adopt/orphan materialization outcomes as well as worker/commit outcomes | `KERNEL` | `RUNTIME_KERNEL` | `DENY` | Observation and store settlement only; no materializing, cleanup, validator execution, or commit |

Workers receive none of these kernel capabilities. `fs.write` continues to
authorize only allowed staging/proposal paths, not access to the governed root.
Materialization verifies that path authority from the frozen run grants.
Each transition names one capability; checks of contract, grants, suspension,
and evidence are preconditions, not additional transition capabilities.

## 6. Transition rows

`CAND` means a current complete `CandidateObservation`; `CVR(pass)` and `CRVW`
mean the frozen qualifying receipt/attestation rules with this exact candidate
input. `SNAP`, `WR`, `CR`, and decision tokens retain DESIGN-01 meanings.
All rows emit audit events before exposing changed state. Candidate observation
publication has an earlier evidence event than the transition citing it; the
operation link, `READY` state, and these events become visible atomically.

The following bounded addition to transition-matrix §8 prevents a second
cycle: candidate review/commit cannot require workspace criteria to be `MET`
before the proposed change has landed. It grants no stage-satisfaction path.

| Composition condition | Candidate operations permitted, subject to all subordinate gates |
|---|---|
| Project `ACTIVE`, stage `RUNNING` or `AWAITING_VALIDATION`, active run, all suspensions `NONE` | Materialize, validate, review/attest candidate, authorize and commit candidate. In particular, allow candidate commit in `AWAITING_VALIDATION`. |
| Project `ACTIVE`, stage `AWAITING_REVIEW`, active run, all suspensions `NONE` | Authorize/commit an already current candidate; no new materialization or candidate validation here |
| Any other combination | No new candidate effect; frozen decision, observation, recovery, and the explicit cleanup rules still apply |

Candidate review is a subordinate evidence operation and does not require the
run to enter `REVIEWING`. Candidate receipts may cause the existing entry into
validation states, but cannot discharge the workspace-evidence guards for
advancement out of them toward satisfaction.

### 6.1 `CandidateMaterialization.status`

| From | To | Preconditions / effect | Required evidence | Capability | Supervised | Autonomous |
|---|---|---|---|---|---|---|
| `∅` | `PLANNED` | Valid active run/contract, resolved source receipt and input; derive and persist all plan fields and reserve worktree; no competing owner | `WR`, current source `SNAP` | `candidate.materialize` | `AUTO` | `AUTO` |
| `PLANNED` | `MATERIALIZING` | Effect barriers clear; suspension `NONE`; scope/write grants valid; clean base verified under lease; durable identity/ownership before first filesystem effect | `WR`, source `SNAP` | `candidate.materialize` | `AUTO` | `AUTO` |
| `MATERIALIZING` | `READY` | Exact proposals materialized; complete direct observation equals prediction; inputs frozen; publish observation and link | New candidate observation, becoming `CAND` with this transition | `snapshot.take` | `AUTO` | `AUTO` |
| `PLANNED`, `MATERIALIZING`, `READY` | `DISCARDING` | Failure, drift, supersession, cancellation, or owner run/contract ends; persist `discard_reason`, revoke currency; stop/quiesce readers and resolve any commit outcome before cleanup | — | `candidate.materialize` | `AUTO` | `AUTO` |
| `DISCARDING` | `DISCARDED` | After reconciliation, under lease, restore only attributable staging changes to committed base; prove cleanup/absence; release reservation | — | `candidate.materialize` | `AUTO` | `AUTO` |
| `READY` | `COMMITTED` | Linked intent reached `APPLIED` with matching candidate/tree; release reservation, retain governed revision | `CR` citing candidate | `commit.apply` | `AUTO` | `AUTO` |

Failure before observation produces no `CandidateObservation` and no validation
input. Invalidation may be recorded during suspension; attributable cleanup is
permitted housekeeping after effects are reconciled. New materialization and
commit remain denied. Unknown files, ownership, or live effects prohibit
cleanup and release of the reservation.

### 6.2 Validation and commit rows replacing the affected frozen rows

| Entity: from → to | Preconditions / effect | Required evidence | Capability | Supervised | Autonomous |
|---|---|---|---|---|---|
| Validation: `AUTHORIZED → EXECUTING` | Pinned input resolves to isolated complete candidate; command, scope, context, budgets, and grants pass | `CAND` as `input_snapshot_id` | `validation.execute` | `AUTO` | `AUTO` |
| Validation: `EXECUTING → COMPLETED` | Pinned command finished; mint result for the exact input; only intact measured input can qualify as `PASS` | `ValidationReceipt` bound to `CAND` ID | `validation.attest` | `AUTO` | `AUTO` |
| Intent: `∅ → PROPOSED` | Candidate provenance and exact mutations/base/target/tree agree; materialization is `READY`; no other live intent claims it; persist unique `operation_token` and trailers | `WR`, `CAND` | `commit.propose` | `AUTO` | `AUTO` |
| Intent: `PROPOSED → AUTHORIZED` | All mandatory candidate validations/reviews covered by immutable preconditions; no blockers; candidate, base, grants, and decisions current | `CAND`, `CVR(pass)`/`CRVW` sets | `commit.authorize` | `CONFIRM` | `AUTO` |
| Intent: `AUTHORIZED → APPLYING` | Under repository lease, recheck all bindings/currency, base head/ref, entire candidate, and absence of foreign index entries; persist `APPLYING` with durable `operation_token`, epoch, and candidate link before staging/commit effects | `CAND`, same qualifying precondition evidence | `commit.apply` | `AUTO` | `AUTO` |
| Intent: `APPLYING → APPLIED` | Stage exact candidate paths, pin and verify the entire staged tree, then commit already materialized contents with no content-transforming hooks; token carried by revision; verify parent, target, full tree and exact diff; `actual_tree_digest = candidate.tree_digest = expected_tree_digest` | `CR` with candidate link and independent workspace `post_snapshot_id` | `commit.apply` | `AUTO` | `AUTO` |
| Intent: `APPLYING → FAILED` | Proven commit failure or observed divergent revision; audit the actual failure; uncertainty goes to recovery instead | Divergent `CommitReceipt` and `ESC(OPEN)` if a revision exists; — if proven no revision (no fabricated receipt) | `commit.apply` | `AUTO` | `AUTO` |

Stage/run lifecycle rows are not widened to consume candidate evidence.
Candidate work occurs as subordinate operations within the active run; it does
not mark workspace mechanical criteria `MET`. Workspace validation rows,
validation error/timeout/cancel rows, commit blocked/denied rows, review quorum
and independence, and stage closure retain their frozen rules. Drift discovered
before `APPLYING` prevents commit and invalidates the candidate. A revision
that exists but diverges still invokes `CM-INV-1` and integrity suspension.

## 7. Crash between materialization and commit

| Ordering requirement | Durable record / external attribution |
|---|---|
| Before worktree allocation or writes | Materialization plan and exclusive ownership, keyed by `materialization_id`, are appended. A kernel ownership marker outside the candidate file namespace carries the same ID before proposal writes. Marker contents alone are never trusted over the log. |
| During materialization | Use atomic replacement per file and preserve the base revision. A recoverable partial tree contains only known before/after entries from that plan. Unsupported partial effects are ambiguous, not grounds for a broad reset. |
| After writes, before validation | Flush completed contents; seal, directly measure, and publish observation. A filesystem seal without a durable observation cannot be cited by a receipt. |
| Before commit | Persist intent identity, candidate link, `APPLYING` state, and token-bearing commit metadata before the first staging/commit effect. Hold/fence the repository writer through commit verification. |
| After commit | Settle receipt and workspace post-snapshot; append separate intent/materialization transition events. A crash between these store updates is reconciled from the same token and candidate link. |

Extend `RUN-INV-3`, `G-9`, and the single reconciliation derivation in
transition-matrix §5.1 to `CandidateMaterialization`. Every old-epoch
non-terminal materialization is `PENDING`, including `PLANNED`, `READY`, and
`DISCARDING`. No new worker, validation, materialization, or commit effect on
its run may start until all relevant operations are resolved. Reconciliation
results take precedence over epoch-derived defaults, as in DESIGN-01.

Existing lease and cancellation mechanisms must fence old writers/validators
before recovery can conclude an effect is absent. Recovery reconciles linked
commit tokens before deciding the fate of staging. `recovery.reconcile` itself
only reads external state and persists its conclusions; it cannot terminate a
process under the guise of observation.

| Observed crash boundary | Reconciliation transition / result | Subsequent action |
|---|---|---|
| Plan durable, no materialization effect; committed base clean, no commit token | `PLANNED` or `MATERIALIZING → DISCARDING`, reason `MATERIALIZATION_FAILED`, `ORPHANED` | Ordinary cleanup confirms absence and releases ownership. Any retry is a new materialization after gates pass. |
| Partial materialization, unambiguously owned and each entry a planned before/after value; base/ref unchanged, no token | `MATERIALIZING → DISCARDING`, reason `MATERIALIZATION_FAILED`, `ADOPTED` (failure established) | Ordinary cleanup reverses only attributable changes; then a fresh materialization may be requested. |
| Complete sealed tree, crash before observation or before `READY` persistence; base/ref unchanged, no token | `MATERIALIZING → READY`, `ADOPTED`; recovery directly walks the tree, verifies full provenance/prediction, and mints one observation with `attribution = RECONCILED` | No worker rerun or automatic commit. New validation executes only after barriers clear. |
| Observation durable, crash during validation/review/approval wait; tree and bindings still exact | `READY → READY`, `ADOPTED`; retain the same observation ID | Completed receipts remain usable only if current. Interrupted validation is reconciled as an execution attempt; absence of a receipt never means `PASS`. A rerun is a new, authorized validation attempt. |
| Old intent `PROPOSED`, `BLOCKED`, or `AUTHORIZED`; no token, base/ref and candidate exact | Intent status unchanged, `ORPHANED` as in the frozen pre-apply rule; materialization `READY → READY`, `ADOPTED` | Continue only after all evidence/authority checks. No commit was initiated by this intent. |
| Intent `APPLYING`; no token; base/ref unchanged; tree/index contain only the exact candidate and attributable staging | Intent `APPLYING → FAILED`, `ORPHANED`; materialization remains `READY`, `ADOPTED` | No blind commit retry. A new intent/token and authorization may cite the still-current candidate. |
| Exactly one token-bearing revision matches intent, candidate, parent, and tree | Intent `APPLYING → APPLIED` under `recovery.reconcile`, `ADOPTED`; mint `CommitReceipt(attribution = RECONCILED)` if absent. Materialization `READY → COMMITTED` under the same capability, with its own event | Adopt once, release reservation. Never materialize or commit again for that intent. If receipt already exists, verify it and settle only the missing materialization transition. |
| Exactly one token-bearing revision diverges | Intent `APPLYING → FAILED`, `ADOPTED`; divergent reconciled receipt and `CM-INV-1` suspension | Candidate loses currency; reserve/quarantine staging until governed rollback resolves the revision. Cleanup cannot erase or replace a landed revision. |
| Crash during attributable cleanup | `DISCARDING → DISCARDING`, `ADOPTED` after read-only confirmation of ownership, unchanged base, and known remaining before/after entries | Ordinary cleanup can finish under its own capability. If already clean, settle `DISCARDED` under `candidate.materialize` without further filesystem changes. |
| Source/context no longer current, but private staging and absence of a commit are fully attributable | `READY → DISCARDING`, appropriate drift/end reason, `ADOPTED` | Stale receipts and approvals persist; clean up normally. |
| Multiple token matches, unexpected ref/head movement without a matching token, unknown content/ownership, or an effect whose termination/outcome cannot be established | Status retained, `UNRESOLVABLE`; `Escalation(RECOVERY_AMBIGUITY)` and integrity suspension | No new effect, cleanup, or reservation release until ambiguity is resolved. Tree equality alone never attributes a commit. |

These are additional reconciliation rows, each `AUTO` in both modes and using
only `recovery.reconcile`, except the explicitly subsequent ordinary actions.
The narrow amendment to `CM-INV-3` is that **known candidate dirt is not an
unknown commit**: no token plus unchanged committed base/ref plus an exactly
attributed candidate establishes that no revision landed. Unexplained dirt or
a moved base still fails closed. Recovery never repairs a tree to make that
predicate true.

## 8. Discard and retention

| Trigger | Candidate lifecycle | What persists |
|---|---|---|
| Required validation/review fails and the controller selects rework or abandonment | Invalidate, stop readers, `DISCARDING → DISCARDED`; replacement gets a new materialization and observation ID | Old observation, results, proposals, and discard events |
| Validation retry over unchanged input | May stay `READY` within existing retry/budget policy; no edits allowed | Each attempt/result separately |
| Superseded proposals, base/input/context drift, contract revocation/expiry, run termination, cancellation | Immediately revoke eligibility; cleanup only after effects are settled | Evidence and invalidation reason; old approvals never revived |
| Successful commit | `READY → COMMITTED`; consume reservation and uncommitted candidate status; keep governed checkout at landed revision | Observation and commit link; candidate receipt IDs unchanged |
| Ambiguous recovery | Quarantine/reserve; do not discard unknown or possibly committed effects | Plan, available observations, receipts, and escalation |

| Object | Lifetime / retention |
|---|---|
| `CandidateObservation`, its manifest, source-receipt binding, base/proposal content closure, candidate diff, and citing receipts | `PERMANENT` evidence under evidence-model §6: retained before archive; later deletion/redaction only under existing explicit decision and tombstone rules. Keep referenced base/content artifacts sufficient to audit/reconstruct the measured tree independently of the directory. |
| Materialization plan and lifecycle events | Durable audit history under the existing append protocol and retention rules; never rewritten to erase an attempt |
| Uncommitted files, ownership marker, reservation, validation scratch | Transient operational resources. Release/remove when safely discarded or consumed by commit; retain while needed by readers or recovery. These are not substitutes for retained evidence. |

Discard means ending eligibility and cleaning up physical staging. It does
**not** delete the observation or change what a receipt measured. Redaction
continues to preserve hashes and chain continuity and can make evidence
unrecoverable; it never authorizes recreating a missing payload under its old ID.

## 9. Statements in `design-01-frozen` amended and left untouched

Only the named deltas below supersede frozen statements. All other DESIGN-01
statements remain in force; the frozen files themselves remain unchanged.

| Frozen source / statement | Amendment |
|---|---|
| `domain-model.md` §8.2, **W-INV-2**; `worker_provider.md` **WP-2** application wording | Explicit user-checkout/governed-worktree distinction; allow kernel materialization before commit while workers still only propose (§1, §5) |
| `domain-model.md` §7.1–§7.3.1 input fields; **V-INV-2**, **RA-INV-4** | Add operation input pinning and widen only the listed validation/review references; candidate-specific currency without receipt rebinding (§3–§4) |
| `domain-model.md` §8.3–§8.4, **CM-INV-2**, **CM-INV-3** | Required candidate links, measured-tree binding, commit-only forward apply, durable materialization identity, and the narrow known-staging recovery exception (§3, §5–§7) |
| `domain-model.md` §9.A, **HD-INV-4**; `transition-matrix.md` §7.5 | Candidate-bound decisions for commit-intent subjects and candidate invalidation as a staleness cause (§3–§4) |
| `domain-model.md` §11 cardinality | Run → materializations: `1:0..n`; receipt → materializations: `1:0..n`; materialization → observation: `1:0..1`; observation → receipts/intents: `1:0..n`, at most one live intent and at most one matched commit |
| `domain-model.md` §12, **G-1** | Add `CandidateObservation` to admissible `required_evidence`, limited to the candidate/commit rows; no new authority class (§4, §6) |
| `domain-model.md` **RUN-INV-3**, **G-9**; `transition-matrix.md` §5–§5.1 and §9.3 recovery prohibitions | Include materialization operations/identities and candidate effects in the existing reconciliation barrier; recovery remains observational (§7) |
| `transition-matrix.md` §0.1, §1.2, §7.1, §7.4, §8 | Materialization subject to effect/suspension gates; add candidate evidence tokens and subordinate/composition rows, allow candidate commit during `AWAITING_VALIDATION`, replace affected validation/commit rows, specify safe discard housekeeping (§5–§7) |
| `authority-matrix.md` §2.4, §2.6, §6 | Add kernel `candidate.materialize`; extend `snapshot.take` and reconciliation subjects; clarify governed target and committing half of `commit.apply` (§5) |
| `evidence-model.md` §2.1–§2.2, §3.2.1, §5–§5.1, §6–§7 | Classify candidate measurement as evidence; extend effect attribution, candidate currency/replay, decision currency, retention, and evidence exports to include candidate provenance (§3–§8) |
| `worker_provider.md` §6 steps 9–12 | Insert materialization/observation before candidate validation; candidate results feed commit preconditions. Workspace satisfaction still requires workspace evidence (§4–§6) |

| Frozen source / statement | Left untouched |
|---|---|
| `domain-model.md` §0.1 `Path`/`Glob`; §6.1 contract scope and command/spec fields; `schema/stage_contract.schema.json` | Workspace-relative path vocabulary, scope include/exclude semantics, pinned commands, immutable contract and activation authority |
| `domain-model.md` §9.D `RealitySnapshot`, **RS-INV-1**; `evidence-model.md` §4 | No root/target addition; sole truth about user workspace; complete workspace evidence required for stage satisfaction |
| `domain-model.md` **S-INV-1..4**, **W-INV-1**, **W-INV-3..4**, **V-INV-1**, **RA-INV-1..3**, **G-2..8**, **G-10** | Claims/evidence/authority separation, receipt minting authority, outcome-preserving adoption, single transition capability, audit continuity, and stage/axis invariants |
| `domain-model.md` **CM-INV-1**; `transition-matrix.md` §7.4 rollback/publication rules | Divergence suspends; rollback remains governed; publication is separately authorized and never implied by commit |
| `domain-model.md` **HD-INV-1..3**; `authority-matrix.md` axioms, role/grant tables and mode gates | Human authentication, evidence shown, nonce consumption, least authority, no worker kernel grants, supervised commit confirmation |
| `transition-matrix.md` project/stage/run lifecycle enumerations and workspace satisfaction rows | No new stage state; candidate success does not close a stage or run |
| `worker_provider.md` lookup/invoke separation, **WP-15..17**, recovery and provider boundaries | No provider replay during recovery, no new worker authority, no candidate-dependent provider protocol |
| `evidence-model.md` artifact integrity, hash-chain construction, append protocol, redaction rules; `schema/events.schema.json` | Reuse existing event envelope and payload mechanism; no changed hashing, evidence erasure, or alternate log |
| `roadmap_adapter.md` and frozen `design/review/*` | No changes to roadmap semantics, adapters, or historical review records |
