# COU01-S3 — Execution-core integration and evidence handoff

**Dispatch:** `NOT_READY` — requires bound repository and accepted `COU01-S1/S2`.  
**Parent:** `PRD-COU-01`.  
**Obligations:** closes this PRD's evidence contribution for `REQ-COU-001..006`, `009..014`, `031`, `033`, `035` without claiming whole-system acceptance.

## Read now

1. `../PRD.md` §§9–11.
2. both predecessor slice completion records and exact accepted candidate binding.
3. `../../architecture/verification-and-readiness.md` rows `VER-COU-001/002/004..007/022/026..030`.

## Worker outcome

Integrate the two accepted execution slices, add/repair execution-specific tests, and provide a candidate/evidence record that PRD-02 and PRD-04 can bind to without re-deriving lifecycle semantics.

## Owned surface

Execution-core tests/fixtures and integration fixes inside PRD-01-owned symbols only. If integration exposes an assertion-engine or reporting semantic change, stop and route it to the named PRD/architecture owner.

## Required result record

Report: exact repository revision + local diff identity; changed objects/files; compiler/runtime used for checks; each `VER` contribution run and result; source-compat compile status if available; any unrun target-specific checks; and the exact active-context interface revision offered to PRD-02.

The slice exits only if execution-core tests pass on the bound test environment and no open defect contradicts R3. That is local implementation evidence, not release acceptance.
