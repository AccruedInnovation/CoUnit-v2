# PRD Authoring Assignments — R3

These are architecture-to-PRD assignments, not worker packets. All four are `READY_FOR_PRD` under the R3 approval in `SRC-020`. The fixed references below are package-relative and bind to `COUNIT-ARCH-R3` / `2026-09-09-r3` unless they name an external source. This authorizes PRD elaboration, not implementation or release.

## Shared authoring gates

- `GATE-COU-001` — **source and authority gate: PASS.** `SRC-001` is packaged and digest-matched; `SRC-020` explicitly approves the R2 basis and the accepted R3 closure.
- `GATE-COU-002` — **assertion semantic gate: PASS.** `ADR-COU-017` is the approved successor to contradicted `ADR-COU-007` and fixes assertion evaluation, first-failure logging, and maximum-per-invocation count semantics.
- `GATE-COU-003` — **predecessor implementation gate:** later implementation/integration work uses accepted outputs of named predecessor PRDs; this is not an architecture-authoring input unless stated.
- `GATE-COU-004` — **release qualification gate:** the integrated implementation passes the required CODESYS/compiler/runtime evidence before release claims.

## PRD-COU-01 — Execution core and lifecycle

- **id:** `PRD-COU-01`
- **architecture_baseline:** `COUNIT-ARCH-R3` / `2026-09-09-r3`; predecessor R1 is historical.
- **capability_ids:** `CAP-COU-01`
- **outcome:** design the repaired runner/suite/test lifecycle so normal and sequential runs terminate truthfully with bounded storage, one execution authority and safe task/context handling.
- **scope:** in — runner states/disposition, suite registration/invocation, test registration/name/order/skip/finish, abort/error finalization, task binding, task/project platform calls. Out — assertion comparison internals, xUnit writer internals, multi-task runs, production-control execution.
- **allocated_requirement_ids:** `REQ-COU-001..006`, `REQ-COU-009..014`, `REQ-COU-031`, `REQ-COU-033`, `REQ-COU-035`. Assertion-storage and multi-scan assertion requirements `REQ-COU-007/008` belong to PRD-02. For spanning requirements, this PRD owns public runner/test APIs (`REQ-COU-001`), suite/test bounded writes (`REQ-COU-004`), and task/project platform calls (`REQ-COU-031`).
- **contribution_obligations:** provide the active test identity/context consumed by PRD-02; provide terminal suite/test/run state consumed by PRD-03; provide active test invocation boundaries used by PRD-02 assertion ordinal reset; keep platform-failure policy consistent with `ISC-COU-004`; PRD-04 owns final integrated acceptance, not this PRD.
- **fixed_refs:** `architecture-baseline.md` §§4–6, 10, 12–15; `decisions.md` `ADR-COU-001..006`, `008`, `015`; `shared-contracts.md` `IF-COU-001/002`, `ISC-COU-001/004`, `SDE-COU-001/002`; authority is `EXPLICIT_APPROVAL` via `SRC-020`.
- **delegated_design:** exact private enum numeric values/names, private helper shape, bounded lookup mechanics, and exact task-identity API binding against packaged `SRC-001`. No change to public signatures/shared state meaning without architecture review.
- **required_elaboration:** source-object map; exact runner transition table; registration/pre-write guards; empty-suite/zero-suite behavior; ordered cursor sentinel; named-finish behavior; abort/error mapping; task/project adapter calls; concrete unit/integration fixtures and worker slices.
- **dependencies:** `SRC-001` — `SUPPLIED_WITH_ARCHITECTURE`, package path `sources/CoUnitPlaintextExport.zip`, contract `sources.md/SRC-001`, available at PRD authoring, gate `GATE-COU-001` PASS; R3 shared contracts — `SUPPLIED_WITH_ARCHITECTURE`, required at authoring, same gate; future implementation outputs — `CREATED_BY_THIS_PRD`, evaluated by its PRD review before `GATE-COU-003`.
- **acceptance_obligations:** `VER-COU-001/002/004..007/022/026..030`, `QAS-COU-001/003/010/011`, `SCN-COU-002/003/007/008`; prohibited effects include any out-of-bounds write, cross-task state mutation, resumed partial run, or unfinished test counted successful.
- **integration_owner:** CoUnit architecture owner.
- **final_acceptance_owner:** `PRD-COU-04` for integrated technical evidence; CoUnit release/architecture owner for release acceptance.
- **authoring_environment:** read-now route is README → this assignment → architecture §§4–6/10/12–15 → named ADR/IF/ISC/SDE → verification rows. Retrieve-for-check: only runner/suite/test/GVL/public run/test functions and task/project helpers from the digest-matched `SRC-001`. Background: TcUnit history only for a named defect. No source mutation, deployment or release claim. Repository target remains `OPEN-COU-001` and is an implementation-stage fact, not a substitute for `SRC-001`.
- **review_policy:** local execution-state review; boundary review of public API↔runner, runner↔suite, platform task lookup; integrated normal/sequence/abort/restart/cross-task scenarios; recipient self-check now and fresh PRD-stage worker check later. Shared semantic changes return to the architecture owner.
- **open_items:** `OPEN-COU-001`.
- **readiness:** `READY_FOR_PRD`. `GATE-COU-001/002` are satisfied; `OPEN-COU-001` is an implementation-stage repository fact.

## PRD-COU-02 — Assertion engine and safe comparison

- **id:** `PRD-COU-02`
- **architecture_baseline:** `COUNIT-ARCH-R3` / `2026-09-09-r3`.
- **capability_ids:** `CAP-COU-02`
- **outcome:** design all existing assertion families through a safe common comparison/outcome path with bounded memory, correct type metadata, stable first-failure behavior, safe REAL/LREAL and generic `ANY`, with constant-size assertion bookkeeping, stable first-failure behavior, and the accepted max-per-invocation count rule.
- **scope:** in — typed scalar/array wrappers, common outcome reporter, suite-invocation assertion counter, per-test invocation ordinal, `MaxAssertionsPerInvocation`, assertion invocation guard, first failure, first-failure detailed logging, formatting/truncation, and removal/migration of obsolete assertion trackers. Out — public API redesign, result-file publishing, multi-task execution.
- **allocated_requirement_ids:** `REQ-COU-001`, `REQ-COU-004`, `REQ-COU-007..008`, `REQ-COU-015..021`, `REQ-COU-034`, `REQ-COU-037`. Contribution boundaries: assertion public signatures (`001`), assertion bookkeeping writes (`004`), assertion semantics (`007..008`, `015..021`, `034`, `037`).
- **contribution_obligations:** consume active test/context guarantees from PRD-01/`IF-COU-002`; provide first-failure and max-per-invocation assertion-count values to PRD-03; preserve public assertion signatures unless an approved compatibility change says otherwise; do not reintroduce per-assertion identity without an architecture change.
- **fixed_refs:** architecture §§6–8, 12–15; `decisions.md` `ADR-COU-001`, `008..009`, `013`, `017` plus contradicted `ADR-COU-007` as supersession history; `shared-contracts.md` `IF-COU-003`, `ISC-COU-002`; `verification-and-readiness.md` `VER-COU-003/008..014/032`.
- **delegated_design:** helper names/decomposition, typed comparator sharing, bounded formatter lengths, counter representation large enough to guard the configured assertion limit before narrowing to legacy `UINT`, and exact removal/wrapper strategy for obsolete trackers. The PRD may not create a new call-site identity registry.
- **required_elaboration:** exact public assertion-family map from `SRC-001`; scalar/array comparator routes; suite-entry counter reset; current-test ordinal reset/data flow; max-per-invocation count; suite-invocation assertion-limit guard; first-failure write/log transition; REAL/LREAL matrix; `ANY` type/size/string handling; migration/removal of obsolete trackers; exact regression fixtures.
- **dependencies:** `SRC-001` — `SUPPLIED_WITH_ARCHITECTURE`, authoring, `GATE-COU-001`; R3 `IF-COU-003`/`ADR-COU-017` — `SUPPLIED_WITH_ARCHITECTURE`, `GATE-COU-002` PASS; PRD-01 active-context implementation — `PRODUCED_BY_PREDECESSOR`, needed for implementation integration only, `GATE-COU-003`.
- **acceptance_obligations:** `VER-COU-003/008..014/032`, `QAS-COU-002/004/012`, `SCN-COU-001/005`; no invalid access, runtime exception, raw-value/call-site identity history, suppressed branch failure, or scan-count-driven storage growth.
- **integration_owner:** CoUnit architecture owner for shared count semantics; PRD-02 author for local implementation integration.
- **final_acceptance_owner:** `PRD-COU-04` / CoUnit release owner.
- **authoring_environment:** read-now README → this assignment → architecture §§6–8/12–15 → named ADR/IF/ISC/open item → verification. Retrieve-for-check only assertion methods, tracker FBs/DUTs, failure setters and formatter interfaces from digest-matched `SRC-001`; retrieve upstream issues only for the defect being tested. No source mutation/deployment.
- **review_policy:** local assertion-family review; boundary assertion engine↔test-state review; integrated changing-value and branch-changing multi-scan probes; recipient check must explain `ADR-COU-017`, including why `NumberOfAsserts` is not a distinct-call-site count.
- **open_items:** `OPEN-COU-001`.
- **readiness:** `READY_FOR_PRD`; `GATE-COU-001/002` are `PASS`.

## PRD-COU-03 — Results, logging and xUnit publication

- **id:** `PRD-COU-03`
- **architecture_baseline:** `COUNIT-ARCH-R3` / `2026-09-09-r3`.
- **capability_ids:** `CAP-COU-03`
- **outcome:** design the immutable final snapshot, legacy projection, Device Log output and streamed xUnit publisher so counts remain truthful and the externally current report can never be a partial failed publication.
- **scope:** in — snapshot/result schema, count reconciliation, legacy result mapping, Device Log, XML escaping, streaming buffer, file/log platform calls, publication commit/currentness and restart cleanup. Out — test execution algorithm, assertion comparison, public API redesign, multi-task runs.
- **allocated_requirement_ids:** `REQ-COU-001`, `REQ-COU-022..031`, `REQ-COU-036`. Contribution boundaries: public result/config surfaces (`001`), result/report obligations (`022..030`, `036`), file/log platform calls (`031`).
- **contribution_obligations:** consume terminal state from PRD-01 and the approved first-failure/max-per-invocation assertion-count semantics from PRD-02; do not reinterpret `NumberOfAsserts` as distinct source call-site count; keep file/log failure semantics consistent with `ISC-COU-004`; preserve test truth when publication fails.
- **fixed_refs:** architecture §§7–10, 12–15; `decisions.md` `ADR-COU-001`, `010..012`, `016..017`; `shared-contracts.md` `IF-COU-004/005`, `ISC-COU-003/004`, `SDE-COU-003`; `REQ-COU-036`; `SCN-COU-004/006`.
- **delegated_design:** private snapshot/XML writer names, chunk size mechanics, and the target-specific publication commit mechanism. Direct final-path writing is allowed only if it proves `IF-COU-005` external-currentness semantics; otherwise choose staging/replace or another conforming scheme.
- **required_elaboration:** snapshot DUT/legacy mapping; XML escaper/code-point policy; chunk writer; file/log error map; publication staging/commit/restart procedure; stale-staging handling; exact fault-injection and parser fixtures; worker slices.
- **dependencies:** `SRC-001` — `SUPPLIED_WITH_ARCHITECTURE`, authoring, `GATE-COU-001`; R3 result/publication contracts — `SUPPLIED_WITH_ARCHITECTURE`, authoring, `GATE-COU-001`; R3 assertion-count contract (`ADR-COU-017`/`IF-COU-003`) — `SUPPLIED_WITH_ARCHITECTURE`, authoring, `GATE-COU-002` PASS; PRD-02 implementation output — `PRODUCED_BY_PREDECESSOR`, implementation integration, `GATE-COU-003`; PRD-01/02 implementation outputs — `PRODUCED_BY_PREDECESSOR`, implementation integration, `GATE-COU-003`.
- **acceptance_obligations:** `VER-COU-015..021/029/031`, `QAS-COU-005..008/013`, `SCN-COU-004/006`; prohibited effects include failed output becoming current, partial XML at the current path, success banner on failed I/O, or publication changing test pass/fail.
- **integration_owner:** CoUnit architecture owner for shared report/currentness contract; PRD-03 author for publisher integration.
- **final_acceptance_owner:** `PRD-COU-04` / CoUnit release owner.
- **authoring_environment:** read-now README → this assignment → architecture §§7–10/12–15 → named ADR/IF/ISC/SDE → verification. Retrieve-for-check result/log/XML/file objects from packaged `SRC-001`; retrieve `SRC-016` separately if schema-specific JUnit checking is needed because the plaintext archive contains no `.xsd` file; use `SRC-014..016` only as support. No source mutation/deployment.
- **review_policy:** local snapshot/publisher review; boundary snapshot↔publishers and publisher↔filesystem/file-consumer review; integrated I/O failure and restart-during-write probes; consumer must be able to tell current complete output without reading hidden PLC state.
- **open_items:** `OPEN-COU-001`, `OPEN-COU-003`.
- **readiness:** `READY_FOR_PRD`; shared report/currentness and assertion-count semantics are settled. `OPEN-COU-003` is bounded delegated PRD detail.

## PRD-COU-04 — Regression, compatibility and integrated qualification

- **id:** `PRD-COU-04`
- **architecture_baseline:** `COUNIT-ARCH-R3` / `2026-09-09-r3`.
- **capability_ids:** `CAP-COU-04`
- **outcome:** design and later run repeatable regression/compatibility qualification for the full repaired library, with evidence-bound runtime support and final integrated acceptance.
- **scope:** in — defect-to-test map, boundary fixtures, public API compile cohort, report parser/oracles, restart/currentness tests, runtime/compiler matrix, integrated evidence report. Out — implementation ownership of requirements assigned to PRD-01/02/03, release approval itself, physical production-control validation.
- **allocated_requirement_ids:** `REQ-COU-032`. This PRD also owns final integrated verification of the committed `REQ-COU-001..037` set; that verification role does not transfer implementation duties from the producing PRDs.
- **contribution_obligations:** verify contributions under the same accepted revisions; reject mixed-revision evidence; preserve all blocking failures; verify `REQ-COU-001` across public surfaces changed by PRD-01/02/03; verify `ADR-COU-017` assertion semantics and xUnit currentness end to end.
- **fixed_refs:** architecture §§12–15 (`REQ-COU-001..037`, `QAS-COU-001..013`, `FE-COU-001..011`, `CAP-COU-01..04`); `decisions.md` `ADR-COU-001..006`, `008..017`, with `ADR-COU-007` read only as supersession history; `shared-contracts.md` `IF-COU-001..005`, `ISC-COU-001..004`, `SDE-COU-001..003`; verification `VER-COU-001..032`, `SCN-COU-001..008`.
- **delegated_design:** qualification-project layout, fixture names, scripts, evidence file layout and exact runtime-matrix rows within accepted support claims. It may not change expected semantics to match implementation results.
- **required_elaboration:** exact defect-to-test map against available source; concrete fixtures/oracles; representative existing-source compile cohort; max/capacity cases; branch-changing assertion case with the explicit max-per-invocation oracle; file failure/restart currentness case; native CODESYS compile/runtime matrix; final report template and evidence binding.
- **dependencies:** R3 package — `SUPPLIED_WITH_ARCHITECTURE`, authoring, `GATE-COU-001`; exact `SRC-001`/existing source cohort — `SUPPLIED_WITH_ARCHITECTURE`, authoring, `GATE-COU-001` PASS; accepted `ADR-COU-017` assertion contract — `SUPPLIED_WITH_ARCHITECTURE`, `GATE-COU-002` PASS; accepted PRD-01/02/03 implementations — `PRODUCED_BY_PREDECESSOR`, qualification execution, `GATE-COU-003`; actual CODESYS compiler/runtime access — external future qualification input, `GATE-COU-004`.
- **acceptance_obligations:** own `VER-COU-023..025` and final integrated disposition of `VER-COU-001..032`; no release support claim without exact environment evidence; no local-pass aggregation can override a failed spanning requirement.
- **integration_owner:** `PRD-COU-04` for qualification assembly.
- **final_acceptance_owner:** CoUnit release/architecture owner.
- **authoring_environment:** read-now README → this assignment → architecture requirements/quality/capabilities → all verification/gates → shared contracts. Retrieve check-specific source/test cohorts from packaged `SRC-001`; retrieve target tooling/version details at qualification planning/execution. No production deployment or release declaration.
- **review_policy:** local verification-design review; boundary coverage for all five IF contracts plus platform adapter; integrated normal/failure/restart/migration-currentness scenarios; PRD-stage fresh worker-consumption review; release owner decides final acceptance.
- **open_items:** `OPEN-COU-001`, `OPEN-COU-002`.
- **readiness:** `READY_FOR_PRD`. Runtime execution remains future qualification under `GATE-COU-004`, not an architecture-authoring blocker.
