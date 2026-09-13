# GR-10 Git transactions

`design/` remains identical to `design-01-frozen`. The transaction follows
transition-matrix §7.4, domain-model §8.3–8.4 and DESIGN-01-RESIDUE R-1–R-5.

| Step | Enforcement |
| --- | --- |
| Intent | Persist the token and trailers before applying. Verify scope, protected paths, message and mutation preimages. Authorization checks the expected parent and branch. |
| Apply | Reconciliation and completeness gates apply. Under the repository lease, re-read state, persist `APPLYING`, verify the base and apply the specified mutations. Only an `AUTHORIZED` intent can initiate application. |
| Stage | `stage(paths)` accepts explicit files and deletion paths. Direct `add .`, `add -A`, empty staging, directories, pathspec directives, protected paths and symlink escapes are refused before launching Git. Literal pathspec mode supports filenames containing glob characters. |
| Verify staged diff | Compare the entire staged content/mode index with the intent's predicted index. Check the frozen content-tree digest and exact changed paths, including both endpoints of renames. Unrelated pre-staged changes, content changes, mode changes and no-op intents abort before commit. |
| Commit | Copy the verified tree into a private index, recheck parent and branch, refuse a pending merge, and commit that index. Git environment overrides are removed; hooks and signing are disabled. Commit messages use explicit verbatim cleanup. |
| Receipt | Persist the observed commit SHA, parent list, native Git tree ID, frozen content-tree digest, subject, body hash, exact paths, per-path content changes, diff artifact and operation token. The receipt hash binds the observations. |
| Verification | Compare all receipt fields with repository observations, and compare those observations with the intent, including modes and unique token attribution. Divergence raises integrity escalation and suspends the run and project. |
| Recovery | Look up the persisted token across refs and reflogs. Adopt the observed revision with the same full verification as direct application; never call commit. Receipt, post-snapshot, audit events and intent settlement share a SQLite transaction. Repeated settlement returns the existing receipt. |
| Publish | `Controller.publish_commit` and `GitRepository.publish` always deny `commit.publish`. The adapter command allowlist rejects `push`, unknown commands and command-line alias/configuration tricks before subprocess execution. |

The body hash is SHA-256 over every UTF-8 message byte after the first newline,
including the blank separator and runtime evidence/token trailers. The native
Git tree ID supplements the frozen digest, whose path-to-content preimage is
unchanged. Rename receipts report the source deletion and destination creation;
this preserves both exact paths without relying on Git's rename heuristics.

`Controller.propose_commit(run_id, path=..., content=..., message=...)` retains
its existing single-file convenience interface. The transaction consumes the
intent's mutation sequence and supports CREATE, MODIFY, DELETE, RENAME and CHMOD.
`verify_commit(intent_id)` re-observes a persisted receipt. Aborted staging may
leave the declared worktree/index changes available for inspection. Recovery
establishes whether anything committed before another attempt can proceed.

The existing repository lease serializes cooperating controllers. It is not an
OS lock preventing an unrelated process from changing Git refs or worktree
files; the adapter rechecks refs immediately before Git's commit command, and
verifies the landed revision afterward. Publication remains unavailable.

Physical storage version is now 3. Existing stores without the receipt columns
are refused explicitly through the GR-03 schema check; this pre-release project
still has no migration path. The domain model version remains `0.1.0`.

Tests exercise real repositories, staged divergence before the commit command,
private-index isolation, every recorded receipt field, the publication boundary,
and SIGKILL during direct receipt persistence and during adoption. The original
R-1–R-5 tests also run. `bin/check-gr10-mutations` runs `bin/mutate` for each
marked guard; each removal must fail a test and each restored full suite must
pass. Concurrent runs use independent temporary Git worktrees.

Verified result: **518 tests pass**, including all 415 original tests. All
**43 guard mutations are killed**, and every restored full suite passes. The
[checked guard inventory](evidence/gr10-mutations.json) records the guard
fingerprints, failing/restored suite summaries and evidence log paths. The
[complete attempt manifest](../.evidence/gr10/manifest.json) also retains the
initial mutation diagnostics and their successful follow-up checks.
