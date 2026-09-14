# GR-08: governed inference relay

Design basis: `design-01-frozen`, especially worker_provider WP-4, WP-7,
CF-4 and CF-8; authority-matrix AX-10/AX-11 and §5.1; evidence-model AS-4.
No frozen design files, validation executor, or ProcessTransport were changed.

| Requirement | Enforcement | Evidence |
|---|---|---|
| Worker-only egress | `WorkerRelayTransport` keeps bubblewrap `--unshare-all`, an empty home and cleared environment. Only an invocation's Unix socket is mounted. An HTTP shim inside that namespace forwards to ToolBridge; the controller alone performs HTTPS. | A real sandboxed subprocess reaches a local TLS fixture through the bridge while direct host TCP fails. The same probe through unchanged ProcessTransport and ValidationExecutor cannot reach host TCP, find the bridge socket, or read the ambient key. |
| One HTTPS origin | Kernel configuration pins scheme, host and port. Request parsing rejects other origins, userinfo, malformed targets and control characters. TLS verification is mandatory; ambient proxy variables are ignored. No redirect is followed, including redirects within the permitted origin. | Two TLS servers count requests. Other hosts/ports/schemes and all 301/302/303/307/308 redirects are refused; the other server receives zero requests. An untrusted certificate is refused. |
| Live invocation grant | `net.request` requires `net.egress.allowlist` in both the invocation grant and tool surface. The bridge replays the activation's actual grant source immediately before each upstream request, with lease, suspension and epoch checks. | SUPERVISED policy and missing grants cause zero requests. A live authenticated human grant succeeds; revocation, expiry, staleness, consumption, authentication changes and governance changes block subsequent requests. AUTONOMOUS policy grants retain the existing GR-06 rules. |
| No credential in provider input | Kernel resolution requires an authenticated human `secret.read` grant and a separate single-action approval naming the secret. Both are consumed before resolution. Only the relay retains the resolved value. | The worker receives a local HTTP endpoint and a public CLI auth placeholder. The TLS fixture observes the injected credential; request artifacts, prompts, environment, adapter journals and all other persisted bytes do not contain it. |
| Check before every sink | Salted fingerprint checks precede artifact writes, event payload/envelope appends, SQLite state and adapter journal writes, fake-provider log lines, diagnostics, and worker/result processing. | Tests plant the canary in stdout, stderr, claims, mutations, progress, error messages, event fields, log lines, response bodies and response headers. They assert safe failure and inspect every persisted file. Boundary tests check that no artifact or event was added on refusal. |
| Restart protection | The state store durably saves only the secret name, random salt, fingerprint and byte length. Providers share this checker without receiving secret values. | Reopening StateStore still rejects the canary without resolving the secret again. Persistence contains neither the value nor its unsalted hash. |

## Operation

`InvocationBridge.call` exposes `net.request` with these exact arguments:

```json
{
  "url": "https://configured-origin.example/v1/messages",
  "method": "POST",
  "headers": {"Content-Type": "application/json"},
  "body": "{}"
}
```

Only GET and POST are supported. Host, credentials, framing, proxy and cookie
headers are kernel-owned; optional protocol headers are operator-selected.
Results contain HTTP status, Content-Type and a UTF-8 body. Response bytes are
bounded and buffered, including SSE, so a secret split across network reads
cannot escape through streaming. A rejected tool call returns DENIED and
records AUTHORITY. A detected output leak discards the tainted value and
records a failed invocation with a safe `SECRET_LEAK` code.

The HTTP shim is a transport detail: it translates each API request into a
fresh ToolBridge call. It never knows the upstream origin or credential. The
controller services the Unix socket on the thread that owns its StateStore;
no SQLite connection is shared with a request-handling thread.

The bridge lease also ends at the worker's wall-clock budget. An independent
watchdog interrupts an upstream socket at the request deadline, including a
response that keeps delivering small chunks. Authority is checked again after
TLS connection setup and before sending HTTP request bytes.

## Configuration

Configure the relay before assembling worker context. The run must already
have an activated contract and an admissible `net.egress.allowlist` grant.
The project ceiling must also include `secret.read`, which is exercised by the
kernel and is never added to the worker's invocation capabilities.

The secret grant is an authenticated `GRANT_CAPABILITY` decision covering the
run and naming `secret.read`. The separate `APPROVE` decision has subject
`CAPABILITY/secret.read`, scope `SINGLE_ACTION`, and `chosen` equal to the secret
name. Both cite human-visible evidence; neither may be stale, expired or used.
These decision IDs come from the application's authenticated decision flow.

```python
from gruntime.adapters.claude_code import ClaudeCodeProvider
from gruntime.adapters.relay_process import WorkerRelayTransport

controller.configure_inference_relay(
    activated_run_id,
    origin="https://api.anthropic.com",
    secret_name="worker-inference",
    resolve_secret=secret_manager.resolve,
    grant_decision_id=secret_grant_id,
    approval_id=secret_approval_id,
    credential_header="x-api-key",
    credential_prefix="",
    protocol_headers=ClaudeCodeProvider.relay_headers,
)
provider = ClaudeCodeProvider(
    governance_directory / "providers",
    transport=WorkerRelayTransport(operator_selected_executable),
    read_artifact=controller.store.artifact_bytes,
)
controller.register_provider(provider)
invocation = controller.create_invocation(
    activated_run_id, prompt=b"Implement the contracted change",
    provider_id=provider.provider_id,
)
receipt = controller.invoke(invocation.invocation_id)
```

The Claude adapter uses its documented
[`ANTHROPIC_BASE_URL` gateway setting](https://code.claude.com/docs/en/llm-gateway).
`ANTHROPIC_API_KEY=governed-local-bridge` is a public placeholder to select CLI
API authentication; it is stripped and never used as the upstream credential.
No live commercial inference call is part of the test suite. CLI-shaped
subprocesses and local TLS fixtures exercise the complete bridge path without
billing or external credentials. Existing token/cost metering remains unchanged.

## Reproduction

```sh
bin/baseline
.venv/bin/python bin/check-gr08-mutations
bin/baseline
```

The mutation runner weakens each marked GR-08 guard individually. A kill must
be an actual pytest failure, never a collection error; the restored selection
must pass after each mutant. It restores source even when a test raises or
times out. The machine-readable report is in `docs/evidence/gr08-mutations.json`.

| Final verification | Result |
|---|---|
| Existing baseline before implementation | 1,056 passed |
| Full suite after implementation | 1,198 passed; no skips (142 added tests) |
| New guards | 74/74 mutation-killed; every restored test selection passed |
| Frozen design | Identical to `design-01-frozen` |
| ProcessTransport and ValidationExecutor | Source unchanged; actual OS isolation exercised |
