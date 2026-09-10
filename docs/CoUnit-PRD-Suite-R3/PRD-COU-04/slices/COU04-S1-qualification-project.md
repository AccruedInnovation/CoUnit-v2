# COU04-S1 — Native qualification project and regression corpus

**Parent:** `PRD-COU-04` / `CAP-COU-04`  
**Status:** `NOT_READY`  
**Reason:** active implementation repository/toolchain and accepted PRD-01/02/03 candidate are not yet bound; fresh packet-only recipient review has not run.

## Outcome and allocation

Create the native CODESYS qualification project/tests that exercise the accepted candidate under `VER-COU-001..018`, `022`, `026..030`, and `032`, plus architecture scenarios `SCN-COU-001..003`, `005`, `007`, `008`. This slice creates tests and fixtures; it does not change CoUnit semantics.

## Entry gate

Before dispatch, bind all of:

- accepted implementation candidate and writable repo paths (`OPEN-COU-001`);
- R3 or authorized successor architecture;
- actual CODESYS Development System/compiler and required library references;
- accepted PRD-01/02/03 predecessor outputs;
- exact qualification-project location;
- fresh recipient-consumption pass for this packet.

## Required reading — read now

1. `../PRD.md` §§1–6, 9–11;
2. `../contracts/qualification-contract.md` §§1–5, 8;
3. `../../architecture/verification-and-readiness.md` §§1–4;
4. accepted PRD-01/02 execution/assertion contracts;
5. `../qualification/defect-to-verification-map.csv`.

Retrieve source declarations and exact producer contracts only for the test being written. The complete historical architecture review is background, not required simultaneous context.

## Reference inventory

- R3 architecture: `SUPPLIED_WITH_PRD` as unchanged copy under `../../architecture/`.
- exact source snapshot `SRC-001`: `SUPPLIED_WITH_PRD` at `../../architecture/sources/CoUnitPlaintextExport.zip`.
- accepted implementation candidate: `PRODUCED_BY_PREDECESSOR`, unavailable until bound/accepted.
- qualification project/tests: `CREATED_BY_THIS_SLICE`.
- actual CODESYS toolchain: externally provisioned entry prerequisite; record exact version before execution.

## Settled design and steps

1. Create one native test application/project that can run the candidate in one cyclic task and, for cross-task tests, a second bounded task.
2. Add dedicated suites grouped by runner lifecycle, capacity, assertion values/types, task/platform failures, and restart/reinit.
3. Each test has a direct oracle from `verification-and-readiness.md` and PRD contracts. Do not derive expected results from the implementation under test.
4. Capacity tests use configured limits, exercise exactly max then max+1, and snapshot guard-adjacent state so the prohibited write/count change can be detected.
5. Multi-scan boundedness case runs at least 10,000 accepted test-body invocations and observes fixed bookkeeping; do not infer boundedness only from eventual completion.
6. Branch case: invocation 1 executes A at ordinal 1 and passes; invocation 2 executes different B at ordinal 1 and fails. Assert B becomes first failure and final assertion count is 1. Companion first-failure case starts with A failing and proves B still executes later without overwriting A's record.
7. FP/ANY cases use independent expected values, including NaN/Inf/negative/NaN delta, long STRING/WSTRING, descriptor mismatch, and equal/different user-defined representation samples.
8. Runner cases cover zero/one/many suites, ordered skip first/middle/last, final suite, nonzero delay, named finish of noncurrent target, abort/error with open tests, run-mode switch, canonical name whitespace/disabled/duplicate cases, and reinitialization.
9. Cross-task test runs one owner task and one foreign caller; verify the foreign call cannot mutate current suite/test state and the owner later reports framework error.
10. Retain exact test names mapped to VER IDs so evidence can be assembled without inference.

## Allowed choices

Private suite/file names, helper FBs, local fixture structs, and assertion formatting may vary. Do not change public CoUnit calls, expected state categories, assertion count meaning, first-failure rules, or error precedence. Escalate any required shared change to the architecture owner.

## Exit gate

- qualification project builds under the bound compiler;
- all planned tests exist and map to the stated VER IDs;
- harness failures are distinguishable from expected pre-fix product failures;
- test fixtures reach their intended guards;
- evidence contains exact candidate/toolchain binding.

A passing product result is not required to finish authoring the regression corpus, but the slice cannot be accepted as qualification evidence until executed against the accepted candidate.
