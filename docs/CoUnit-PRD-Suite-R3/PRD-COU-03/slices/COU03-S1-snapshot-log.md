# COU03-S1 — Canonical snapshot, legacy projection, and Device Log

**Dispatch:** `NOT_READY` — active repository absent; requires accepted PRD-01/02 terminal/count contracts.  
**Parent:** `PRD-COU-03`.  
**Obligations:** `REQ-COU-001`, `022..026`, `031` log contribution.

## Read now

- `../contracts/reporting-contract.md` §§1–3.
- `../../architecture/shared-contracts.md` `IF-COU-004`, `ISC-COU-003/004`.
- accepted PRD-01 terminal-state and PRD-02 first-failure/count outputs.
- source export: result DUTs, `FB_TestResults`, `FB_CdsTestResultLogger`, `WRITE_DEVICE_LOG`.

## Outcome and fixed work

Before accepting the fixed snapshot representation on a bound target, record its compiled `SIZEOF` and the relevant application/static-memory use. The declared maxima imply at least 80 MiB of snapshot string storage alone; if the target memory budget cannot accommodate the full contract, stop and return to the architecture owner rather than reducing capacity or fields.

1. Add immutable final snapshot built once in `FINALIZING`; validate count invariant before `IsValid` commit.
2. Make `FB_TestResults` expose legacy projection from snapshot rather than incremental partial truth.
3. Copy R3 max-per-invocation assertion count unchanged after range check.
4. Keep legacy failed boolean assertion-failure-only and successful aggregate pass-only.
5. Fix `WRITE_DEVICE_LOG` so plain messages log and long chunks emit left-to-right.
6. Honor `LogExtendedResults`; never suppress failure/framework/final summary/xUnit failure.

Exit evidence: mixed pass/fail/skip/error counts reconcile; no partial snapshot visible; log plain `%s`/no-placeholder cases; verbose flag on/off.
