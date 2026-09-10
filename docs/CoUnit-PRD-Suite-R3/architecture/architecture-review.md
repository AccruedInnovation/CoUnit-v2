# CoUnit Architecture R3 Closure Review

## 1. Current result and scope

**Predecessor reviewed:** `COUNIT-ARCH-R2` / `2026-09-09-r2`  
**Successor:** `COUNIT-ARCH-R3` / `2026-09-09-r3`  
**Mode:** bounded `REVIEW_AND_REVISE` continuation of the R1→R2 adversarial review  
**Governing contract:** v4 Architecture and Design Package Synthesizer (`SRC-019`)  
**Effects:** architecture/source inspection and package revision only; no CoUnit library source mutation, compile/runtime execution, deployment, release, credentials, or physical effect.

R3 closes the three architecture-authoring gates that R2 correctly left open. The package is now **`COMPLETE` / `APPROVED`**, and `PRD-COU-01..04` are **`READY_FOR_PRD`**. This status authorizes PRD elaboration only.

The current user/architecture-owner instruction supplies the two missing authority facts: R2 is accepted, and the recommended `OPEN-COU-008` closure is accepted. The newly supplied CoUnit archive also matches R2's exact expected digest.

## 2. Closure findings and evidence

### `RF-COU-001` / `OPEN-COU-006` — `FIXED_AND_RECHECKED`

The supplied `CoUnitPlaintextExport(1).zip` hashes to `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`, exactly matching `SRC-001`. R3 copies those bytes unchanged to `sources/CoUnitPlaintextExport.zip`. ZIP inspection found no absolute/parent-traversal paths or symlinks. The archive contains 423 `.exp` files plus its README.

Targeted source intake verified the object families needed for the prior findings, including `FB_coUnitRunner`, `FB_TestSuite`, `FB_Test`, `FB_AssertResultStatic`, assertion methods, `FB_TestResults`, `FB_CdsTestResultLogger`, `FB_xUnitXmlPublisher`, GVLs and result DUTs. This closes availability and allows package-relative PRD source lookup.

### `RF-COU-002` / `OPEN-COU-007` — `FIXED_AND_RECHECKED`

`SRC-020` records explicit owner acceptance of R2 and of the recommended assertion closure. R3 therefore binds operative decisions to `EXPLICIT_APPROVAL`. It does not claim that the missing historical R1 delegation has been recovered.

### `RF-COU-003` / `OPEN-COU-008` — `FIXED_AND_RECHECKED`

Source inspection strengthens the reason not to invent another implicit call-site key:

- 44 public `Assert*` methods were found under `FB_TestSuite`;
- their input names reduce to `Expected`, `Actual`, `Condition`, `Delta`, and `Message`; none accepts a stable assertion/call-site identity;
- `FB_Test` stores one `AssertionMessage` and one `AssertionType` for the first failure;
- `ST_TestCaseResult.NumberOfAsserts` is a `UINT`;
- the current `FB_AssertResultStatic` attempts value/message/path history and its `ReportResult` implementation never assigns its declared `FoundOne` or `AdditionalIdenticalAssert` variables.

The approved successor `ADR-COU-017` therefore removes persistent assertion identity rather than replacing one guessed key with another. Each assertion executes whenever its call executes. The test records an invocation-local ordinal and the maximum ordinal reached in any one test-body invocation. The existing `MaxNumberOfAssertsForEachTestSuite` setting is retained as a hard bound on total assertion calls in one suite-body invocation. The first failure is one atomic event and the only detailed assertion-failure log for that test.

**Counterexample recheck:** scan 1 runs branch A at ordinal 1 and passes; scan 2 runs a different branch B at ordinal 1 and fails. Under R3 there is no ordinal-keyed history lookup, so B executes and sets first failure. Final `NumberOfAsserts` is `1`, by the explicit max-per-invocation meaning. The original R1 alias defect cannot occur under the written R3 contract.

**Strong rebuttal:** a stable source-location ID could in theory preserve distinct call-site counting. The present public API does not carry caller location, and adding explicit IDs, generated rewrites, or runtime call-stack/source-location machinery would enlarge the public/tooling contract merely to preserve a metric that CoUnit only exposes as `NumberOfAsserts`. R3's simpler metric preserves normal test syntax and the more important failure truth/bounded-memory outcomes. The accepted owner decision resolves the semantic trade-off.

### Additional source-backed correction — R2 JUnit-schema lookup wording

The supplied plaintext archive contains no `.xsd` file. R2 told PRD-03 to retrieve a local JUnit schema from `SRC-001`; that lookup would fail. R3 corrects the reading route: source result/XML objects come from `SRC-001`, while `SRC-016` remains separate supporting material for schema-specific checks. This is a bounded handoff repair and does not change the report contract.

## 3. Source fidelity observations rechecked

The supplied source supports the R1/R2 defect baseline without requiring runtime execution:

- `FB_AssertResultStatic.ReportResult` declares `FoundOne` and `AdditionalIdenticalAssert` but does not assign either before testing them; every accepted call follows the add path under the shown implementation.
- `AddAssertResult` increments `TotalAsserts` and indexes `AssertResults[TotalAsserts]` without a pre-write capacity guard.
- `ReportResult` refreshes `CurrentCycleCount` at the end rather than writing the stored `CycleCount` member.
- `FB_TestSuite.CalculateAndSetNumberOfAssertsForTest` derives counts from stored scalar/array result records.
- `FB_TestResults` stores name/status/failure fields but the inspected body does not copy `FB_Test.GetNumberOfAssertions()` into `ST_TestCaseResult.NumberOfAsserts`.
- `FB_xUnitXmlPublisher.LogTestSuiteResults` writes root `tests` from `NumberOfSuccessfulTestCases`, matching the snapshot README's count defect note.

These are source observations, not claims that a native CODESYS runtime reproduction was executed.

## 4. R3 contract and handoff result

`IF-COU-003` is now complete at architecture depth. PRD-02 owns the local counter/tracker migration and comparator design; PRD-03 consumes the fixed max-per-invocation count without reinterpreting it; PRD-04 owns the branch-changing and result-projection qualification cases. No PRD must discover a shared assertion identity rule.

The exact `SRC-001` archive is `SUPPLIED_WITH_ARCHITECTURE`. The approval and assertion gates are both `PASS`. `OPEN-COU-001..005` remain correctly classified as implementation detail, future qualification, bounded PRD detail, or deferred scope; none is a shared architecture prerequisite.

All four assignments therefore meet the architecture-stage `READY_FOR_PRD` test: fixed shared semantics exist, the source is package-accessible, the architecture is approved, and remaining choices are bounded to their assigned PRDs.

## 5. Validation and limits

Checks run on the content-frozen R3 directory:

- source archive SHA-256 match: `PASS`;
- source ZIP path/symlink safety and inventory (423 `.exp` + README): `PASS`;
- targeted assertion/public-result/source-defect inspection: `PASS` as source analysis;
- 44 public `Assert*` methods found and no explicit stable call-site identity input found: `PASS` as source analysis;
- YAML parse with duplicate-key rejection: `PASS`;
- all 18 canonical handoff fields on all four assignments: `PASS`;
- package identity/status projection: `PASS` (`COMPLETE` / `APPROVED`);
- all four handoff readiness projections: `PASS` (`READY_FOR_PRD`);
- canonical object counts/uniqueness: `PASS` for 37 REQ, 13 QAS, 11 FE, 4 CAP, 32 VER, 5 IF, 4 ISC, 3 SDE, 17 ADR and 4 PRD records;
- PRD allocation union: `PASS`, exactly `REQ-COU-001..037` with no extra committed requirement;
- current open-item table: `PASS`, only `OPEN-COU-001..005`; closed `006..008` remain closure history only;
- package-relative links, manifest artifact presence and Markdown table shape: `PASS`;
- operative-file placeholder/stale-blocker scan: `PASS`.

The final ZIP extraction/byte comparison is a delivery-level check performed after package content is frozen; its result is reported with delivery rather than written back into the package and thereby changing the checked bytes.

Not run and not claimed: native CODESYS compile, simulator/controller tests, target filesystem publication behavior, runtime performance, or a fresh independent post-repair recipient review. These remain downstream PRD/qualification duties, not architecture-stage blockers.

## 6. Current open items

- `OPEN-COU-001`: implementation repository/path — PRD/implementation-stage fact.
- `OPEN-COU-002`: exact compiler/runtime support matrix — future `PRD-COU-04` qualification.
- `OPEN-COU-003`: target-specific xUnit semantic-commit mechanism — bounded `PRD-COU-03` design under fixed `IF-COU-005` behavior.
- `OPEN-COU-004`: duration and extra long date/time assertions — deferred scope.
- `OPEN-COU-005`: protected/custom assertion extension API — deferred scope.

No architecture-authoring blocker remains.

---

# Appendix — R1 adversarial review and R2 repair record

# CoUnit Architecture R1 Adversarial Review and R2 Repair

## 1. Review result and exact scope

**Mode:** `REVIEW_AND_REVISE`  
**Original subject:** uploaded `CoUnit-Architecture-Rebaseline-R1(1).zip`; package `COUNIT-ARCH-R1` / `2026-09-09-r1`  
**Original archive SHA-256:** `0d99336a7ee38de212be1f5af222716f700d05008fdbfeba31077d155bd6b84a`  
**Successor:** `COUNIT-ARCH-R2` / `2026-09-09-r2`  
**Governing architecture authoring contract:** `03-blueprint-architecture-design-package-synthesizer-prompt-v4.md`, version 4, set `harmonized-v4` (`SRC-019`)  
**Effects:** document/archive inspection and revision only; no CODESYS source mutation, native compile/runtime execution, deployment, credentials, spending, publication or physical effect.

R1 claimed `COMPLETE`, `CANDIDATE`, and four `READY_FOR_PRD` assignments. That claim does not survive review. R2 is **`BLOCKED` / `CANDIDATE`**. All four PRDs are `BLOCKED` because the exact required CoUnit source and project-specific authority source are not available; PRD-02/03/04 also depend on an unresolved assertion identity/count rule.

The review completed the available package/internal/shared-contract/handoff assessment. It cannot establish verified fidelity to the original CoUnit assignment or exact 1.2.0.3 implementation because those controlling inputs are missing. No fresh independent recipient was available; post-repair recipient checks are same-context self-review.

## 2. What should remain

The following R1 choices form a coherent candidate architecture and should not be replaced merely because the package was over-ready:

- **One CODESYS library, not a new host service.** The reliability repair does not need a second runtime, network service or new deployment boundary.
- **One run owner and one task binding.** Runner ownership of suite invocation and explicit cross-task rejection removes competing execution authorities while multi-task support remains out of scope.
- **Explicit execution state plus disposition.** This cleanly separates test failure from framework abort/error and supports truthful finalization.
- **Hard pre-write bounds.** Every fixed-capacity write must fail before the write; capacity errors are framework errors, not memory corruption.
- **Canonical test identity and terminal skip.** This supports named finish, ordered execution and result lookup with one test record.
- **Canonical final snapshot.** Device Log, legacy results and xUnit should consume the same final truth rather than maintain competing completion/count facts.
- **Publication failure separate from test truth.** A file-system failure must not turn passing/failing tests into different test results.
- **Bounded typed comparison rules and non-retained run state.** The NaN/Inf/ANY safety direction and fresh-run-on-reinit direction are well matched to a test library, subject to recovered authority/source compatibility.

The review also checked current public TcUnit release data as supporting context; 1.3.1 is still the latest tagged release on 2026-09-09. That outside check supports R1's source register timing but does not replace the missing CoUnit source or assignment.

## 3. Findings and adversarial evidence

### `RF-COU-001` — MAJOR — required authoring source is identified but not accessible

**Kind/obligation:** handoff/readiness defect; Synthesizer v4 §§4, 22, 26–27 require an `EXISTING` dependency to have an actual accessible location/revision and a claimed-ready author to be able to locate its inputs.  
**R1 location:** `sources.md` `SRC-001`; all PRD dependencies/read routes; `verification-and-readiness.md` readiness table.  
**Expected:** a PRD author can retrieve the exact CoUnit 1.2.0.3 source bytes before doing source-mapped design.  
**Actual:** R1 gives only `CoUnitPlaintextExport.zip` and SHA-256 `458aab...c6d48`. The archive is not inside the package and has no stable package-relative, repository, file-library or other accessible locator. Review search by exact filename/digest did not recover it.

**Probe:** start `PRD-COU-01` using only its declared route and attempt its first substantive action: map `FB_coUnitRunner`, `FB_TestSuite`, `FB_Test`, GVL/public functions and task helpers. The route stops at `SRC-001`; the bytes are unavailable. The same failure affects PRD-02/03 and PRD-04's source-compatibility cohort.

**Rebuttal:** the digest precisely identifies the source. True for identity, false for availability. A hash cannot supply the bytes or source object paths.  
**Consequence:** all R1 `READY_FOR_PRD` claims are unsupported; source fidelity and API compatibility cannot be rechecked.  
**Disposition:** `OPEN`; R2 creates `OPEN-COU-006`, lowers all PRDs to `BLOCKED`, and requires a digest-matched accessible source before requalification.

### `RF-COU-002` — MAJOR — material authority/delegation claim is not bound to a project assignment

**Kind/obligation:** authority/source defect; Synthesizer v4 shared authority rules and §§2, 4, 7, 22 require material choices and authoring permission to bind owner, source and scope of authority.  
**R1 location:** `decisions.md` says `DELEGATED_AUTHORITY` means selected under "the user's request to produce the repair architecture"; YAML `authoring_permission_ref` repeats an uncited prose claim. `SRC-017` is workflow instruction, not the CoUnit product assignment.

**Probe:** ask a recipient to locate the exact instruction that delegates public compatibility, one-task scope, float semantics, non-retained restart behavior, and PRD candidate authoring. No package source provides it.  
**Rebuttal:** a candidate architecture need not already be approved. Correct, but `READY_FOR_PRD` still requires the shared decisions to be settled under valid authority; candidate state does not create delegation.  
**Consequence:** this review cannot verify intended outcome, reserved choices or whether R1's new selections were inside the author's authority.  
**Disposition:** `OPEN`; R2 preserves R1's authority labels as historical claims, does not rely on them, creates `OPEN-COU-007`, removes authoring permission, and blocks all PRDs until the assignment/delegation or explicit approval is available.

### `RF-COU-003` — MAJOR — assertion ordinal is not a stable logical assertion identity

**Kind/obligation:** shared architecture/contract defect; Synthesizer v4 §§10–13 and 27 require shared meaning/state rules that allow two conforming components to agree, including multi-scan behavior.  
**R1 location:** `ADR-COU-007`; architecture §7.2; `IF-COU-003`; `REQ-COU-024`; `VER-COU-008`.  
**Expected:** bounded de-duplication suppresses repeat output from the same logical assertion without merging different assertions or falsifying logical assertion counts.  
**Actual:** R1 keys a slot only by `(test index, assertion ordinal)` where ordinal is the order of **executed** assertions in that invocation.

**Analytical counterexample (`SCN-COU-005`):** on scan 1, branch A executes `AssertEquals_INT(..., 'A')` as ordinal 1 and fails. On scan 2, mutually exclusive branch B executes a different `AssertEquals_INT(..., 'B')` as ordinal 1 and fails. Both conform to the written public/multi-scan model. R1 maps both to the same slot/type; B can be treated as a repeated failure of A and the maximum ordinal remains 1. R1's own tests only exercise repeated same-shape calls, so they can pass this defective design.

**Rebuttal:** ordinal is stable if every test executes the same assertion-call shape each scan. True, but R1 does not make that a public contract and such a restriction would itself change the preserved authoring model. The framework's call-based design permits ordinary ST branches in multi-scan tests.  
**Consequence:** PRD-02 cannot safely design de-duplication; PRD-03 cannot fix final logical assertion-count semantics; PRD-04 lacks a valid oracle.  
**Disposition:** `OPEN`; R2 marks `ADR-COU-007` `CONTRADICTED`, fixes the non-aliasing semantic requirement, adds `REQ-COU-037`/`VER-COU-032`, and creates `OPEN-COU-008` for the authorized replacement. The reviewer did **not** select a new material identity algorithm without authority.

### `RF-COU-004` — MAJOR — internal publication status did not protect the external current report artifact

**Kind/obligation:** shared interface/recovery defect; Synthesizer v4 §§10–13, 21 and 27 require the file consumer boundary, partial effects and recovery/currentness to be defined.  
**R1 location:** architecture §9.3 and §5.5; `IF-COU-005`; `SDE-COU-003`; `FE-COU-005`; PRD-03 delegated "direct-path vs temporary-path" strategy.  
**Expected:** CI/human never consumes a partial xUnit artifact as the current successful report.  
**Actual:** R1 requires internal state `FAILED` on I/O failure but allows direct writing to the final path if PRD-03 chooses it. If the file is truncated/partly written before failure, the external file-only consumer can observe that partial artifact despite the PLC enum saying `FAILED`.

**Rebuttal:** CI could query the PLC publication state. R1 names a file consumer and does not require or define such a channel; adding one later would itself be a shared contract change.  
**Consequence:** all local writer checks could pass their internal-state rules while the actor-visible report outcome fails. Restart during writing makes the gap worse because publication state is non-retained while filesystem bytes persist.  
**Disposition:** `FIXED_AND_RECHECKED` at architecture level. R2 adds `ADR-COU-016`, `REQ-COU-036`, external semantic commit/currentness to `IF-COU-005`/`SDE-COU-003`, and `SCN-COU-006`/`VER-COU-031`. The exact target mechanism remains bounded PRD detail. Analytical recheck: a direct-path design now conforms only if it proves the same no-partial-current property. Native runtime proof remains future qualification, not falsely reported as run.

### `RF-COU-005` — MODERATE — spanning producer obligations were assigned to the wrong or only one PRD

**Kind/obligation:** allocation/handoff defect; Synthesizer v4 §22 requires each spanning requirement's producing contributions and one final acceptance owner.  
**R1 location:** PRD allocations for `REQ-COU-001`, `REQ-COU-004`, `REQ-COU-031`; `ELM-COU-08` had no cross-PRD structure contract.  
**Actual:** R1 assigned `REQ-COU-007/008` to PRD-01 even though PRD-02 owns assertion storage/multi-scan assertion behavior; PRD-02 could also alter assertion public signatures and assertion writes without an explicit compatibility/bounded-write contribution; PRD-03 could alter file/log runtime calls but did not own `REQ-COU-031`. PRD-04 might detect the error later, but no producer-side assignment told these PRDs they own that part of the invariant.

**Rebuttal:** each PRD's prose says no major public API redesign and PRD-04 compiles existing tests. This lowers risk but does not define contribution boundaries for minor signature drift, assertion bounds or file/log pointer/result use.  
**Disposition:** `FIXED_AND_RECHECKED`. R2 moves `REQ-COU-007/008` to PRD-02, allocates `REQ-COU-001` to PRD-01/02/03 by surface, `REQ-COU-004` to PRD-01/02 by storage, `REQ-COU-031` to PRD-01/03 by runtime-call family, and adds `ISC-COU-004`. Structural cross-reference recheck passes.

### `RF-COU-006` — MODERATE — machine-readable handoff and completeness evidence overstated usable detail

**Kind/obligation:** handoff/readiness defect; Synthesizer v4 §§20, 22, 26–27 require exact fixed references, dependency contract/phase/gate, task-specific reading routes, complete capability/acceptance links and current recipient evidence.  
**R1 evidence:** all 18 handoff keys existed and YAML parsed, but fixed refs were bare IDs without location/revision/authority; dependencies omitted contract/gate; YAML PRD-04 listed `QAS-COU-001..010` even though canonical architecture has `QAS-COU-011`; capability records were only outcome sentences; all PRDs stayed `READY_FOR_PRD` despite the input failures above.

**Rebuttal:** the human README/prose contained more context. True, which is why this is not a critical schema failure. But the projection claims to be an import-friendly handoff and must agree with the canonical package rather than force hidden recovery.  
**Disposition:** `FIXED_AND_RECHECKED`. R2 enriches fixed refs/dependencies/routes, includes all quality/scenario ranges, expands capability acceptance/dependencies, and makes the YAML/prose readiness agree. YAML parse/reference checks pass; actual source/authority blockers remain visible rather than being called fixed.

## 4. Applied repairs and pending amendments

R2 changes only the architecture/handoff package. No product source was changed.

| R1 issue | R2 canonical change | Authority treatment | Affected PRDs |
|---|---|---|---|
| required source unavailable | `sources.md`, `OPEN-COU-006`, `GATE-COU-001`, status/readiness | records gap only; no source invented | all |
| delegation unavailable | `decisions.md`, `OPEN-COU-007`, null authoring permission | historical R1 claim preserved; no approval invented | all |
| assertion ordinal alias | `ADR-COU-007` contradicted; `REQ-COU-037`, `IF-COU-003`, `VER-COU-032` | reviewer does not choose replacement algorithm; architecture owner required | 02, 03, 04 |
| partial current report | `ADR-COU-016`, `REQ-COU-036`, `IF-COU-005`, `SDE-COU-003`, `SCN-006`, `VER-031` | derived repair of R1's own `OUT-COU-06`/`FE-COU-005`; remains provisional pending authority | 03, 04 |
| spanning allocation gaps | allocations + `ISC-COU-004` | no new product scope; assigns existing shared duties to actual producers | 01, 02, 03, 04 |
| handoff projection drift | YAML/prose/routes/gates/capability detail | structural repair only | all |

Pending architecture action is intentionally small: recover source/authority, then resolve one shared assertion identity/count question. Do not reopen the otherwise coherent runner/result architecture merely because these gates exist.

## 5. Contract, allocation and handoff assessment

### Contracts

`IF-COU-001`, `IF-COU-002`, `IF-COU-004` and the main state/disposition split are coherent at architecture depth. `IF-COU-005` is coherent after the R2 currentness repair. `IF-COU-003` is deliberately incomplete in one place: stable assertion identity/count. That incompleteness is now explicit and blocks dependent authoring instead of being delegated as if it were local detail.

### Allocation

R2's committed requirement set is `REQ-COU-001..037`. Production contributions are allocated to PRD-01/02/03, with PRD-04 owning `REQ-COU-032` production and final integrated verification. The three spanning requirements most likely to be lost at PRD boundaries now have explicit contribution splits. `OPEN-COU-008` remains an architecture-owned predecessor to the assertion/result allocations.

### Handoff

All four assignments contain all 18 canonical fields in both human and YAML forms. Each dependency now identifies classification, source/producer, governing contract, required phase and gate. Each fixed ref identifies a package location/revision and authority state. Each route separates read-now, check-specific source retrieval and background material. This fixes the handoff structure but does not make unavailable input available.

## 6. Coverage, checks and recipient evidence

### Review units completed

1. **Binding/source/authority:** archive identity, package status, source register, governing v4 contract, accessibility and authority claims.
2. **Local execution:** runner/suite/test state, registration/order/finish, task binding, restart and capacity semantics.
3. **Local assertion:** comparison safety, storage/de-dup model, first failure, float/ANY rules.
4. **Local result/publisher:** final snapshot, count rules, Device Log, XML streaming/file effects.
5. **Boundaries:** public API↔core; runner↔suite; assertion↔test state; snapshot↔publishers; publisher↔filesystem/file consumer; platform adapter contributions.
6. **Integrated:** normal/sequence, skip, abort/error, capacity, cross-task, restart, branch-changing assertion, write-failure/restart currentness.
7. **Allocation/handoff:** requirements→PRD contributions, 18 fields, dependency order, reading routes, YAML/canonical agreement.
8. **Successor recheck:** affected contracts, allocation, statuses, YAML, archive contents and same-context recipient consumption.

### Checks not established

- exact CoUnit 1.2.0.3 source fidelity, object names/signatures and source-side defect reproduction — blocked by `OPEN-COU-006`;
- intended outcome/delegation fidelity — blocked by `OPEN-COU-007`;
- final assertion identity/count architecture — blocked by `OPEN-COU-008`;
- native CODESYS compile, CoUnit execution, simulator/controller behavior and filesystem commit primitives — future PRD/runtime qualification;
- genuinely independent post-repair recipient review — unavailable in this session; not claimed.

### Recipient evidence

Same-context consumption was run for all four assignments. Each reader route can now recover outcome, allocation, fixed/shared rules, allowed local design, gates, acceptance and first action. Each also reaches the correct stop condition: PRD-01 stops on source/authority; PRD-02 on source/authority/assertion identity; PRD-03 on source/authority/assertion-count dependency; PRD-04 on exact source plus unresolved shared assertion semantics. No assignment requires the recipient to guess around the blocker.

**Context estimate:** `the core R2 authoring set is about 13,800 words across README, architecture, decisions, shared contracts, PRD assignments, verification and sources, before YAML and this review; each PRD route reads only its named subset plus check-specific source excerpts. The exact source-code contribution is unknown until `SRC-001` is accessible`. These are document word counts and reading-plan estimates, not measured model capacity. Source-code context cannot be estimated accurately until `SRC-001` is available.

## 7. Remaining decisions and delivery

Only these items block architecture authoring:

1. `OPEN-COU-006`: supply the exact `SRC-001` bytes at a stable accessible location and validate SHA-256.
2. `OPEN-COU-007`: supply the original CoUnit rebaseline assignment/delegation, or have the authorized owner explicitly approve the applicable R2 candidate choices and PRD authoring.
3. `OPEN-COU-008`: architecture owner selects a stable assertion de-duplication identity and logical assertion-count meaning that passes `SCN-COU-005`/`VER-COU-032` without breaking approved public compatibility.

`OPEN-COU-001..005` remain later/local/deferred items as classified in `verification-and-readiness.md` and need no action to understand why R2 is blocked.

**Successor archive identity:** `COUNIT-ARCH-R2` / `2026-09-09-r2`, delivered as `CoUnit-Architecture-Rebaseline-R2.zip`. No recursive or embedded archive hash is used.  
**Archive validation:** `PASS` after finalization: a separate extraction was byte-compared with the reviewed R2 directory. No native CODESYS/import/runtime claim follows from that archive check.
