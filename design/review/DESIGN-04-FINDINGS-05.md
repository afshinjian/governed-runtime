# DESIGN-04-FINDINGS-05 — GR-26 final review and OWNER acceptance

| Property | Value |
|---|---|
| Record identifier | `DESIGN-04-FINDINGS-05` |
| Stage | `GR-26` |
| Date | 2026-09-17 |
| Record status | Final immutable review record |
| Reviewed revision | [DESIGN-04 Revision 05](../DESIGN-04-baseline-correction-05.md), after remediation of `GR26-R1`, `GR26-R2` and `GR26-R3` |
| Bound revision SHA-256 | `35f283c3f86ebab2e3130f1d8836ef89c294f194c125073f0801daf5d7ad2c54` |
| Bound revision size | 222661 bytes; 1281 lines |
| Repository HEAD at review and recording | `bfe52264ecf21e85668da4ee98e0bf4685f814d4` |
| Frozen normative comparison | `design-01-frozen`, peeled commit `8fd51193da0f29efb60ddf906fc845bb0dcbaeb3` |
| Independent re-review verdict | **PASS** |
| OWNER disposition | **ACCEPTED** |
| Final verdict for Revision 05 | **ACCEPTED** |

The bound revision is a working-tree document, not part of the HEAD commit above.
Its SHA-256 identifies the exact bytes reviewed and accepted.

## 1. Provenance and scope

The OWNER assigned the same independent GR-26 reviewer to the bounded re-review.
The reviewer authored no DESIGN-04 revision. The prior GR-26 findings were supplied
by the OWNER in the conversation; this record preserves their final dispositions
and the completed re-review's result.

The completed re-review covered only `GR26-R1`, `GR26-R2`, `GR26-R3` and their
direct consequences. It consulted `CLAUDE.md`, Revision 05, the relevant frozen
design text, and the prior evidence in
[DESIGN-04-FINDINGS-03](DESIGN-04-FINDINGS-03.md),
[DESIGN-04-FINDINGS-04](DESIGN-04-FINDINGS-04.md),
[DISPOSITION-01](DISPOSITION-01.md) and
[DESIGN-01-FINDINGS-02-VERIFY-01](DESIGN-01-FINDINGS-02-VERIFY-01.md).
This recording action introduces no findings and does not reopen design review.

## 2. Final finding status

| Identifier | Final status | Completed re-review conclusion |
|---|---|---|
| `GR26-R1` | **CLOSED** | [Revision 05:575](../DESIGN-04-baseline-correction-05.md#L575) defines `pos(D)` from the required decision-recording AuditEvent, selecting the least sequence when the transition emits multiple events. Frozen [domain-model.md:797](../domain-model.md#L797) requires at least one event, and [evidence-model.md:174](../evidence-model.md#L174) and [:187](../evidence-model.md#L187) establish unique sequence positions and authoritative per-project order. [Step 5a:596](../DESIGN-04-baseline-correction-05.md#L596) retires a capability from `G` only for a covering, recorded, non-VOID revocation `R` with `pos(R) > pos(G)`. The rule and its lifetime summaries are consistent. |
| `GR26-R2` | **CLOSED** | [Revision 05:1232](../DESIGN-04-baseline-correction-05.md#L1232) and the contiguous [§8 register:1245](../DESIGN-04-baseline-correction-05.md#L1245) carry the §5.2 denial-reason mapping as `KD-16` and the CAPABILITY subject.id referent as `KD-17`. Both are expressly unresolved and nonblocking for this bounded correction. Registration adds no underlying design for either debt. |
| `GR26-R3` | **CLOSED** | [Revision 05:110](../DESIGN-04-baseline-correction-05.md#L110), [:1120](../DESIGN-04-baseline-correction-05.md#L1120) and [:1208](../DESIGN-04-baseline-correction-05.md#L1208) accurately reproduce the committed owner flags and identify stale prose as non-authoritative. The prior immutable records were unchanged. |
| `DESIGN-04-025` | **RESOLVED** | The lifetime is technically coherent on the repaired rule. The completed re-review separated technical resolution from acceptance of the chosen premises; the OWNER has now accepted those premises. |
| DESIGN-04 Revision 05 | **ACCEPTED** | Independent bounded re-review: PASS. Subsequent explicit OWNER disposition: ACCEPTED. |

For `GR26-R1`, the verified histories are:

| Recorded order | Effect of `R` |
|---|---|
| `G1 → R` | Retires the named capability from `G1`. |
| `G1 → R → G2` | Retires it from `G1`, but not from `G2`. |
| `G1 → G2 → R` | Retires it from both `G1` and `G2`. |

Retirement persists when `R` later becomes EXPIRED, CONSUMED or STALE; VOID is
excluded. The ordering depends on recorded history, not wall-clock or commit
time. The one-granting-decision citation was already required by
[Revision 04 AX-19:512](../DESIGN-04-baseline-correction-04.md#L512).
The completed re-review checked consistency among §5.3, AX-19(c)/(f), R13.26,
§6.5, §0 and KD-9. It found **no new blocking issue caused directly by these
remediations**.

For `GR26-R3`, the authoritative committed
[DESIGN-04-FINDINGS-04 table:155](DESIGN-04-FINDINGS-04.md#L155) records:

| Finding | OWNER blocking flag |
|---|---|
| `DESIGN-04-029` | true |
| `DESIGN-04-030` | true |
| `DESIGN-04-031` | false |
| `DESIGN-04-032` | true |
| `DESIGN-04-033` | true |
| `DESIGN-04-034` | true |
| `DESIGN-04-035` | true |
| `DESIGN-04-036` | true |

These are historical OWNER flags, reproduced without alteration or a new
disposition of the associated implementation findings.

## 3. OWNER disposition

After receiving the PASS re-review, the OWNER explicitly stated in the
conversation:

> OWNER DISPOSITION: ACCEPTED
>
> I accept the chosen design premises in DESIGN-04 Revision 05.

The OWNER directed that the five statuses in §2 be recorded as final and
authorized only creation of this immutable record. This disposition records
acceptance of the exact revision bound above, including its chosen design
premises. Revision 05's earlier pending-acceptance prose describes its state
before this disposition; its bytes remain unchanged.

## 4. Record boundary and authorization

The completed re-review verified that the four normative model files match
`design-01-frozen`, Revisions 01–04 are unchanged, all eighteen pre-existing
review files match HEAD, and DESIGN-04-FINDINGS-04 and DISPOSITION-01 match their
original committed records. Creation of this record preserves those files and
the bound Revision 05. No runtime test or implementation-conformance claim is
made by this document.

This acceptance does not apply the proposed amendments to the frozen model
files or close the outstanding work carried in Revision 05 §8. This action adds
only this review record; it performs no staging, commit, tag, push or stage
transition. Subsequent findings or dispositions must be recorded separately,
preserving this record as historical evidence.

**Separate explicit OWNER authorization is still required for any next stage
or subsequent implementation.**
