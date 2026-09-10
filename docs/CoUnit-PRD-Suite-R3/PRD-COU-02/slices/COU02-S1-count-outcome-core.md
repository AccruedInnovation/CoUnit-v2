# COU02-S1 — Assertion count, common outcome, and first failure

**Dispatch:** `NOT_READY` — active repository absent; also requires accepted PRD-01 active-context implementation.  
**Parent:** `PRD-COU-02`.  
**Obligations:** `REQ-COU-004`, `007..008`, `015..017`, `034`, `037`.

## Read now

- `../contracts/assertion-engine-contract.md` §§1–4, 8–9.
- `../../architecture/shared-contracts.md` `IF-COU-003`, `ISC-COU-002`.
- accepted PRD-01 active-context contract/candidate when available.
- source export: `FB_TestSuite` assertion tracker fields, `FB_AssertResultStatic`, `FB_AssertArrayResultStatic`, `SetTestFailed`, `FB_Test`.

## Outcome and steps

1. Implement one `BeginAssertion` path with pre-write suite-invocation guard.
2. Reset suite counter at runner suite-body entry and test ordinal at each accepted current-test segment.
3. Track only `InvocationOrdinal`, `MaxAssertionsPerInvocation`, `HasFailure`, and first-failure record; no per-call identity/history.
4. Implement `RecordAssertionOutcome` with first-failure fields committed before `IsSet`.
5. Remove old tracker objects from the canonical path.
6. Add branch-change and 10,000-scan tests before adding all comparator families.

Exit evidence must show constant bookkeeping size, branch A ordinal-1 pass then branch B ordinal-1 fail, first failure not overwritten, and capacity+1 failing before counter/storage mutation.
