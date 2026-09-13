# GR-09 validation

The frozen `design/` files are unchanged. GR-09 adds a catalog binding to the
frozen `CommandSpec` execution and `ValidationReceipt` rules. There is no
StageContract authoring service yet: `Controller.bind_validations` pins its
validation slice once per run in the existing append-only event log.

```python
from pathlib import Path
import sys
from gruntime.validation_catalog import (
    ParameterRef, ParameterSchema, ValidationOperation,
)

op = ValidationOperation(
    operation_id="tests.unit", version="1.0.0",
    argv=(str(Path(sys.executable).resolve()), "-m", "unittest", ParameterRef("suite")),
    parameters={"suite": ParameterSchema("string", choices=("test_parser", "test_api"))},
    cwd="tests", env_allowlist=("LANG",), network="NONE", timeout_ms=30_000,
    write_policy="READ_ONLY", side_effect_class="READ_ONLY", safe_to_rerun=True,
)
controller.validation_catalog.register(op)
controller.bind_validations(run_id, {
    "unit": {"operation": "tests.unit@1.0.0", "parameters": {"suite": "test_parser"}},
})
receipt = controller.execute_validation(run_id, "unit")
```

| Setting | Enforcement |
| --- | --- |
| Operation | Explicit `id@MAJOR.MINOR.PATCH`; unknown, unversioned and `latest` references refused. Versions cannot be replaced. Contracts also pin the catalog digest. |
| Parameters | Exact names and Python scalar types; booleans do not count as integers. Strings have length bounds and optional choices. Integers have inclusive bounds. |
| Path | Workspace-relative declared root; parameter relative to that root. Reject absolute paths, dot segments, backslashes and control characters. Canonical paths must remain under the declared root. |
| argv | Fixed absolute executable, fixed literal arguments, and `ParameterRef` arguments. Each parameter occupies one argument. No shell interpolation, splitting or formatting. Catalog authors are trusted to choose programs that treat those arguments as data. |
| cwd | Catalog-relative workspace directory, canonicalized before execution. |
| Environment | Captured runtime environment filtered by catalog names; executor calls accept no environment override. |
| Network | `NONE` uses a private network namespace. `ANY` shares the host network and must declare `EXTERNAL` side effects. `ALLOWLIST` returns `ERROR` before starting the validator because this backend cannot enforce destination allowlists. |
| Writes | `READ_ONLY`: read-only workspace and temporary directories. `SCRATCH`: additionally allows `/scratch`. `WORKSPACE_COPY`: also allows the disposable workspace copy. No policy writes to the source checkout. |
| Timeout | Catalog milliseconds; kills the process group and sandbox PID namespace on expiration. |
| Snapshot | Latest observation must be `COMPLETE` and cover the whole workspace. The executor copies only indexed files, verifying their bytes against the snapshot before launch. Symlink escapes and changed content are refused. Unobserved/untracked files are unavailable. |
| Receipt | Runtime-owned event with operation identity/digest, typed input values, snapshot id/hash, exit code, PASS/FAIL/ERROR/TIMEOUT, stdout/stderr artifact references, duration and environment/toolchain digests. |
| Recovery | Durable attempt event precedes execution. A missing receipt holds the run barrier. Recovery cancels interrupted attempts only when `safe_to_rerun` is true and the side-effect class is `READ_ONLY` or `SANDBOX_WRITE`. Other attempts remain unresolved and raise `RECOVERY_AMBIGUITY`. Recovery never executes a validator. `retry_validation` rechecks the catalog and all execution gates. |

The Linux backend requires `/usr/bin/bwrap` with working user, mount, PID and
network namespaces. System tools and libraries under `/usr`, `/bin`, `/lib`,
`/lib64` and `/etc` are mounted read-only. Missing tools or unavailable sandbox
facilities yield ERROR with no unsandboxed fallback. This implementation uses
exit-code verdicts; structured result parsers and full contract activation,
capability grants and budgets belong to subsequent contract integration.

The tests run real subprocesses and real SIGKILL crash seams. Guard mutations
are checked using `bin/mutate`; their individual pytest results are retained
under `.evidence/`. `bin/check-gr09-mutations` runs the complete guard inventory
sequentially and restores each mutation before advancing.

Verified result: 415 tests pass (310 existing and 105 GR-09 tests); all 44
guard mutations were killed, with every restored suite green. The combined
[mutation manifest](../.evidence/gr09/manifest.json) identifies each guard and
its evidence log. Independent groups used temporary worktrees with `--only`
to avoid concurrent mutations of the same checkout.
