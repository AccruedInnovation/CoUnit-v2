# PRD-COU-04 Qualification Contract

**Contract ID:** `CON-COU04-001`  
**Revision:** `2026-09-09-r3`  
**Owner:** `PRD-COU-04` qualification assembly  
**Authority:** detailed qualification design delegated by `COUNIT-ARCH-R3`; this contract cannot change `REQ-COU-001..037`, `IF-COU-001..005`, `ADR-COU-017`, or PRD-01/02/03 behavior.

This file is normative for the qualification implementation. Architecture files remain authoritative for shared product semantics.

## 1. Candidate evidence binding

Every executed qualification observation MUST bind:

1. exact accepted implementation candidate revision and content identity;
2. exact R3 contract revision or authorized successor;
3. exact CODESYS Development System/compiler version;
4. exact controller/runtime and OS/CPU environment;
5. exact project/fixture and library references;
6. test configuration affecting behavior, including CoUnit limits and xUnit path/options;
7. project-wide `STRING` encoding mode and, for `LEGACY_SINGLE_BYTE`, the exact byte-to-Unicode mapping identity plus its independent evidence source;
8. the command/action used and retained output/evidence;
9. result `PASS`, `FAIL`, `INCONCLUSIVE`, or `NOT_RUN`.

Evidence from different bindings may support separate rows. It MUST NOT be merged into one support claim unless the release owner explicitly defines a larger support class and every member is qualified or bounded by stated equivalence evidence.

## 2. Qualification result rules

- `PASS`: the exact semantic oracle for that check was met and no prohibited effect occurred.
- `FAIL`: the oracle was violated, including an unexpected crash, corrupt state, wrong count/type, partial-current report, source edit required for compatibility, or missing expected diagnostic.
- `INCONCLUSIVE`: execution occurred but environment/tool failure or incomplete observation prevents the semantic conclusion.
- `NOT_RUN`: no qualifying execution occurred.

No count of passing checks can override one applicable `FAIL`. `INCONCLUSIVE` and `NOT_RUN` do not become `PASS` through review.

## 3. Public API compatibility cohort (`VER-COU-023`)

Two layers are required:

### A. Source-surface drift check

`qualification/public-api-surface.csv` records the architecture-preserved compatibility surface recovered from exact `SRC-001`: all seven public lifecycle/test façade functions (including `TEST_ORDERED`), all 44 `FB_TestSuite.Assert*` methods, the `FB_TestSuite` public inheritance/declaration surface, `I_TestResults` plus its two methods, the three legacy result DUTs, `E_AssertionType`, and `GVL_Param_coUnit`. This is **not** a claim that no other declaration exists; it is the set whose source compatibility is explicitly preserved by R3 and PRD-03. An implementation worker compares the accepted candidate's corresponding public declarations against this inventory. Exact declaration hashes are evidence anchors, not a demand to preserve private variables/comments when public source compatibility is unchanged. Any intentional compatibility-surface difference requires architecture-owner review under `REQ-COU-001`.

### B. Native existing-project compile cohort

Before `VER-COU-023` may pass for release, bind at least one real downstream project that already consumes the current CoUnit public API and compile it against the accepted candidate with **no normal test-source edits**. Generated/synthetic tests may supplement but cannot replace this cohort. Record project identity privately when needed; retained evidence may redact customer/business content while keeping compiler errors and relevant call signatures.

If no existing project is available, `VER-COU-023` remains `NOT_RUN`; do not claim source compatibility from the surface CSV alone.

## 4. Defect and requirement closure

`qualification/defect-to-verification-map.csv` is the review aid that maps the known exact-source defect/risk classes to `VER-COU-001..032`. The architecture `verification-and-readiness.md` remains canonical for requirement-to-VER allocation.

For final integrated disposition:

- verify every applicable `VER-COU-001..032` against one compatible candidate/contract binding or a stated unaffected-evidence rule;
- preserve all failures and inconclusive results;
- link each result to its producer PRD and evidence path;
- check `SCN-COU-001..008` across the joined evidence, not by assuming local passes imply the scenario;
- verify `REQ-COU-032` only from actual runtime matrix rows.

## 5. Native runtime matrix

Canonical row fields are in `qualification/runtime-matrix.csv`; semantics are in `runtime-matrix-schema.md`.

A support claim is exact-row evidence unless the release/architecture owner authorizes a stated compatibility family. Minimum row work is:

1. clean/native compile of the candidate and qualification project;
2. run all-suites path;
3. run sequence path;
4. assertion semantic suite;
5. xUnit publication/report parser suite;
6. restart/currentness suite;
7. capture exact component/runtime versions and disposition.

A row may be `SUPPORTED` only when **all** row-level group statuses are `PASS`: compile, all-suites, sequence, assertion semantics, xUnit, restart/currentness, public compatibility, complete applicable `VER-COU-001..032`, and integrated `SCN-COU-001..008`. The row also binds its project-wide `STRING` encoding mode. A `UTF8` row uses `legacy_mapping_id=N/A`; a `LEGACY_SINGLE_BYTE` row must bind a non-`UNBOUND`, non-`N/A` mapping identifier backed by retained compiler/runtime evidence and a mapping-sensitive raw-byte xUnit case. Any required `FAIL`, `INCONCLUSIVE`, or `NOT_RUN` status, or an unbound required mapping, makes the row `UNSUPPORTED` or `UNQUALIFIED` as appropriate.

## 6. xUnit independent host oracle

`tools/verify_xunit.py` is supplied with this PRD. It uses Python's standard XML parser to check:

- XML parses;
- root and suite `tests/failures/errors/skipped` counts equal observed testcase terminals;
- each testcase has at most one of `failure`, `error`, or `skipped` and no unknown result-state child;
- optional `assertions` values are nonnegative integers;
- when expected JSON supplies case details, name/class, assertion count, terminal kind, failure type/message, and error message match;
- optional expected JSON matches the independently parsed logical result.

It intentionally does **not** reproduce the PLC's XML generation algorithm and does not prove file-currentness or filesystem commit behavior. `fixtures/xunit/mixed-results.xml` is its positive author-time fixture; `bad-count.xml`, `bad-terminal.xml`, and `bad-assertions.xml` MUST fail for their intended reasons.

At dispatch, if Python is unavailable, the qualification worker may use another independent standards XML parser only if it preserves the same semantic checks and records the substitute. It may not accept the PLC publisher's own success flag as its only oracle.

## 7. Integrated evidence record

The final evidence report MUST contain:

- candidate/contract/toolchain/runtime bindings;
- executed verification table for `VER-COU-001..032`;
- integrated scenario table for `SCN-COU-001..008`;
- public API cohort result;
- runtime matrix rows and exact support dispositions;
- known failures/inconclusive checks;
- release recommendation separated from release-owner acceptance.

`PRD-COU-04` may assemble and recommend; the CoUnit release/architecture owner performs final acceptance.

## 8. Change invalidation

Re-run the smallest affected set, plus counterpart/integrated checks, when:

- public declarations change: `VER-COU-023` plus affected semantic tests;
- runner/suite/test lifecycle changes: PRD-01 VERs plus affected `SCN-001/002/003/007/008`;
- assertion core changes: PRD-02 VERs plus `SCN-001/005/008` and result projection when count/failure fields change;
- snapshot/log/xUnit/file publication changes: PRD-03 VERs plus `SCN-001/004/006/007`;
- platform adapter or compiler/runtime changes: affected native tests and `VER-COU-025`; file/task changes also re-run `VER-021/022/027/031` as applicable;
- only evidence layout/text changes: structural review only when semantics and candidate binding are unchanged.

Never retain a `PASS` across a semantic change merely because the test file itself did not change.
