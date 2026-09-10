# COU01-S1 — Runner state, suite registry, and task ownership

**Dispatch:** `NOT_READY` — `OPEN-COU-001` active repository/baseline not bound.  
**Parent:** `PRD-COU-01`, `CAP-COU-01`.  
**Obligations:** `REQ-COU-002..005`, `013..014`, `031`, `033`, `035`; contributes runner half of `REQ-COU-001`.

## Read now

1. `../PRD.md` §§1–7 and §11.
2. `../contracts/execution-core-contract.md` §§1–3, 5, 10–12.
3. `../../architecture/shared-contracts.md` `IF-COU-002`, `ISC-COU-001/004`, `SDE-COU-001`.
4. `../../review/source-observations.md` runner/task rows.

Retrieve from `../../architecture/sources/CoUnitPlaintextExport.zip`: `FB_coUnitRunner`, `FB_TestSuite/FB_init`, `GVL_coUnit`, `GetCurTaskInfo`, `RUN`, `RUN_IN_SEQUENCE`, abort path.

## Worker outcome

Make the runner the only run/suite authority; add explicit state/disposition/mode/epoch; make suite registration pre-write bounded; bind each run to one task; use only the atomic `DWORD` violation latch from a foreign task; make abort/framework error terminal and non-retained.

## Owned implementation surface

After repository binding, this slice owns the active repository equivalents of `FB_coUnitRunner`, its run/abort methods, runner-private DUTs/helpers, suite-registration method, and task-identity adapter. It may update `GVL_coUnit` only to remove authority or maintain compatibility projections. It must not edit assertion comparison methods or xUnit/file writer internals.

## Fixed steps

1. Add semantic variants/types from the normative contract.
2. Replace temporary completion counters with runner state/disposition/mode.
3. Add bounded suite registration with count commit after successful write.
4. Bind first valid top-level call to current task handle.
5. Add `CrossTaskViolationLatch : DWORD`; foreign task calls only `TEST_AND_SET` and returns.
6. Owner task checks the latch before/after suite calls and finalizes `FRAMEWORK_ERROR` on violation.
7. Implement all-suites and sequence progression without temporary finished counters.
8. Make reinitialization start `IDLE`; no `RETAIN`/`PERSISTENT` current-run state.
9. Leave public function signatures unchanged.

## Required checks

- zero/one/many suite state traces for both modes;
- max suites and max+1 with canary values around registry where feasible;
- second-task call changes only the atomic latch before the owner handles it;
- task lookup failure never dereferences a failed pointer/result;
- abort/error leaves no known `OPEN` test counted successful after later PRD integration;
- mode switch cannot resume execution.

Stop and report if the active repository cannot provide a task-identity API with checked failure behavior or cannot compile `TEST_AND_SET(DWORD)` on the required compiler. Do not replace it with unsafe foreign-task complex-state writes.
