# DISPOSITION-01 — owner blocking dispositions

Baseline: `0f540c4` (`0f540c47e61b26b3d2bd6565f90a2de5d0f8c7d7`).

## Purpose

Five findings records were committed without owner blocking dispositions:
[DESIGN-03-FINDINGS-01.md](DESIGN-03-FINDINGS-01.md),
[DESIGN-03-FINDINGS-02.md](DESIGN-03-FINDINGS-02.md),
[DESIGN-04-FINDINGS-01.md](DESIGN-04-FINDINGS-01.md),
[DESIGN-04-FINDINGS-02.md](DESIGN-04-FINDINGS-02.md) and
[DESIGN-04-FINDINGS-03.md](DESIGN-04-FINDINGS-03.md). Per the review method a record
freezes findings, not dispositions, and the blocking flag is the owner's; in the two
DESIGN-03 records the blocking column carries the reviewer's recommendation only, and in
the three DESIGN-04 records it was left blank and reserved. This record is the single
place where the owner sets that flag for all of them. It lists one table per record,
carrying each finding that record raises as a new id, with the severity and any reviewer
blocking recommendation copied verbatim from the record and the record line cited; it does
not restate, summarise or re-judge any finding, and it changes no earlier record. Every
`owner blocking` cell is `—` (not yet dispositioned) and every `owner note` is empty,
pending the owner's pass.

## DESIGN-03-FINDINGS-01

New ids raised by this record; the disposition rows for no earlier record exist here (it is
the first). The record line is cited in the `id` cell. The record declares its `blocking`
column to be "this review's recommendation; no owner disposition exists for this document"
([DESIGN-03-FINDINGS-01.md:41](DESIGN-03-FINDINGS-01.md)); its values are copied verbatim.

| id | severity | reviewer recommendation | owner blocking | owner note |
|---|---|---|---|---|
| DESIGN-03-001 (L45) | BLOCKER | blocking: true | true | |
| DESIGN-03-002 (L46) | BLOCKER | blocking: true | true | |
| DESIGN-03-003 (L47) | BLOCKER | blocking: true | true | |
| DESIGN-03-004 (L48) | BLOCKER | blocking: true | true | |
| DESIGN-03-005 (L49) | BLOCKER | blocking: true | true | |
| DESIGN-03-006 (L50) | BLOCKER | blocking: true | true | |
| DESIGN-03-007 (L51) | MAJOR | blocking: false | true | |
| DESIGN-03-008 (L52) | MAJOR | blocking: false | true | |
| DESIGN-03-009 (L53) | MAJOR | blocking: false | true | |
| DESIGN-03-010 (L54) | MAJOR | blocking: false | true | |
| DESIGN-03-011 (L55) | MINOR | blocking: false | false | |
| DESIGN-03-012 (L56) | MINOR | blocking: false | false | |
| DESIGN-03-013 (L57) | MINOR | blocking: false | false | |
| DESIGN-03-014 (L58) | MINOR | blocking: false | false | |
| DESIGN-03-015 (L59) | MINOR | blocking: false | false | |
| DESIGN-03-016 (L60) | MINOR | blocking: false | false | |
| DESIGN-03-017 (L61) | MINOR | blocking: false | false | |

## DESIGN-03-FINDINGS-02

New ids only. The record's "Disposition of DESIGN-03-FINDINGS-01" judgments on `-001`…`-017`
([DESIGN-03-FINDINGS-02.md:11](DESIGN-03-FINDINGS-02.md)–:27) are not carried here. The
record declares its `blocking` column to be "this review's recommendation; no owner
disposition exists for this document"
([DESIGN-03-FINDINGS-02.md:52](DESIGN-03-FINDINGS-02.md)); its values are copied verbatim.

| id | severity | reviewer recommendation | owner blocking | owner note |
|---|---|---|---|---|
| DESIGN-03-018 (L56) | BLOCKER | blocking: true | true | |
| DESIGN-03-019 (L57) | BLOCKER | blocking: true | true | |
| DESIGN-03-020 (L58) | BLOCKER | blocking: true | true | |
| DESIGN-03-021 (L59) | MAJOR | blocking: false | true | |
| DESIGN-03-022 (L60) | MINOR | blocking: false | false | |
| DESIGN-03-023 (L61) | MINOR | blocking: false | false | |
| DESIGN-03-024 (L62) | MINOR | blocking: false | false | |
| DESIGN-03-025 (L63) | MINOR | blocking: false | false | |

## DESIGN-04-FINDINGS-01

New ids raised by §7. The record's column is "blocking (owner reserved)"
([DESIGN-04-FINDINGS-01.md:295](DESIGN-04-FINDINGS-01.md)) and every such cell is blank:
"every blocking cell is deliberately blank for the owner"
([DESIGN-04-FINDINGS-01.md:293](DESIGN-04-FINDINGS-01.md)). The record therefore makes no
blocking recommendation for any of these findings.

| id | severity | reviewer recommendation | owner blocking | owner note |
|---|---|---|---|---|
| DESIGN-04-001 (L297) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-002 (L298) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-003 (L299) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-004 (L300) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-005 (L301) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-006 (L302) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-007 (L303) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-008 (L304) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-009 (L305) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-010 (L306) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-011 (L307) | MINOR | none — blocking cell blank (owner reserved) | false | |
| DESIGN-04-012 (L308) | MINOR | none — blocking cell blank (owner reserved) | false | |
| DESIGN-04-013 (L309) | MINOR | none — blocking cell blank (owner reserved) | false | |
| DESIGN-04-014 (L310) | MINOR | none — blocking cell blank (owner reserved) | false | |

## DESIGN-04-FINDINGS-02

New ids raised by §7 only; the record's §2 dispositions of the fourteen earlier findings
([DESIGN-04-FINDINGS-02.md:166](DESIGN-04-FINDINGS-02.md)ff.) are not carried here. The
record's column is "blocking (owner reserved)"
([DESIGN-04-FINDINGS-02.md:376](DESIGN-04-FINDINGS-02.md)) and every such cell is blank:
"All blocking slots remain blank for the owner"
([DESIGN-04-FINDINGS-02.md:397](DESIGN-04-FINDINGS-02.md)). No blocking recommendation is
made for any of these findings.

| id | severity | reviewer recommendation | owner blocking | owner note |
|---|---|---|---|---|
| DESIGN-04-015 (L378) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-016 (L379) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-017 (L380) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-018 (L381) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-019 (L382) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-020 (L383) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-021 (L384) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-022 (L385) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-023 (L386) | MINOR | none — blocking cell blank (owner reserved) | false | |
| DESIGN-04-024 (L387) | MINOR | none — blocking cell blank (owner reserved) | false | |

## DESIGN-04-FINDINGS-03

New ids raised by §7 only; the record's §4 dispositions of the twenty-four earlier findings
([DESIGN-04-FINDINGS-03.md:173](DESIGN-04-FINDINGS-03.md)ff.), whose own column is likewise
"blocking (owner reserved)", are not carried here. The §7 column is "blocking (owner
reserved)" ([DESIGN-04-FINDINGS-03.md:301](DESIGN-04-FINDINGS-03.md)) and every such cell is
blank; the record instructs "Keep all owner blocking slots untouched"
([DESIGN-04-FINDINGS-03.md:318](DESIGN-04-FINDINGS-03.md)). No blocking recommendation is
made for any of these findings.

| id | severity | reviewer recommendation | owner blocking | owner note |
|---|---|---|---|---|
| DESIGN-04-025 (L303) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-026 (L304) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-027 (L305) | MAJOR | none — blocking cell blank (owner reserved) | true | |
| DESIGN-04-028 (L306) | MINOR | none — blocking cell blank (owner reserved) | false | |

## Row counts

| record | rows |
|---|---|
| DESIGN-03-FINDINGS-01 | 17 |
| DESIGN-03-FINDINGS-02 | 8 |
| DESIGN-04-FINDINGS-01 | 14 |
| DESIGN-04-FINDINGS-02 | 10 |
| DESIGN-04-FINDINGS-03 | 4 |
| total | 53 |
