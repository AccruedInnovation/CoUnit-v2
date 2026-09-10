# COU01-S2 — Test identity, registration, ordering, finish, and queries

**Dispatch:** `NOT_READY` — requires bound repository and accepted `COU01-S1`.  
**Parent:** `PRD-COU-01`.  
**Obligations:** `REQ-COU-001`, `004`, `006`, `009..012`, `033`; provides PRD-02 invocation context.

## Read now

1. `../contracts/execution-core-contract.md` §§4, 6–9, 13.
2. `../../architecture/shared-contracts.md` `IF-COU-001/002`, `SDE-COU-002`.
3. `../../review/source-observations.md` suite/public-facade rows.

Retrieve from source archive: `FB_TestSuite` declaration; `AddTest`, `AreAllTestsFinished`, `SetTestFinished`, `IsTestFinished`, `GetTestByPosition`; public `TEST`, `TEST_ORDERED`, `TEST_FINISHED`, `TEST_FINISHED_NAMED`, `IS_TEST_FINISHED`; `FB_Test` declaration.

## Worker outcome

Use one canonical test record/name and stable index; make skip terminal; remove runtime cycle count from semantic identity; ensure capacity+1 cannot write; make named finish touch only its named target; establish the active-test segment boundary PRD-02 uses to reset assertion ordinal.

## Owned implementation surface

Own the active repository equivalents of suite/test lifecycle storage and the six public test lifecycle functions. Do not change public signatures or assertion comparator behavior.

## Fixed steps

1. Add `TestRecords[]`, count, ordered count/cursor, and `HasBeenInvoked` per contract.
2. Add one name canonicalizer and use it for all register/lookup/finish/query paths.
3. Replace cycle-count duplicate logic with runner epoch.
4. Implement pre-write max-test guard and commit count last.
5. Initialize disabled tests as `SKIPPED` and terminal; after committing a newly registered ordered terminal record, immediately advance the ordered cursor across terminal leading records.
6. Implement ordered cursor with `UDINT` exhausted sentinel and one shared `AdvanceOrderedCursorPastTerminalRecords()` path for registration-time terminal records and later terminal transitions.
7. Implement `TEST_FINISHED` and named finish rules exactly.
8. Make `AreAllTestsFinished` depend only on invocation + terminal records.
9. Remove core reads of `GVL_coUnit.CurrentTestNameBeingCalled`, `CurrentTestIsFinished`, and `IgnoreCurrentTest`; keep only projections if compatibility requires them.
10. Expose active suite/test index + `ShouldExecuteCurrentTest` to PRD-02 through the runner/suite internal contract.

## Required checks

- max and max+1 test registration;
- names: whitespace, `disabled_` mixed case, empty after prefix, case-sensitive normal names;
- duplicate twice in one epoch versus once per later epoch;
- skipped first/middle/last ordered tests, including an explicit check that registering `disabled_A` at cursor 1 advances the cursor before `B` is evaluated;
- named finish A while B is active; unknown name; terminal idempotence;
- empty suite after first valid invocation;
- query without valid suite returns false without pointer dereference.

Any proposed public signature change or alternate name identity is an architecture change and must stop this slice.
