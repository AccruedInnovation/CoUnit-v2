# Source Register — R3

## Source precedence

R3 uses the v4 Architecture and Design Package Synthesizer as the governing architecture-stage contract for this package. The CoUnit source snapshot is implementation evidence, not authority to preserve defects. Existing public behavior and source syntax are compatibility inputs unless an authorized decision changes them.

R3 preserves R1/R2 source identities and now supplies the exact CoUnit source bytes package-relative. A digest identifies the source; the packaged path makes it directly usable by PRD authors.

| ID | Source | Class | Binding, availability and use |
|---|---|---|---|
| `SRC-001` | `sources/CoUnitPlaintextExport.zip` | OBSERVATIONAL | **SUPPLIED_WITH_ARCHITECTURE.** CoUnit 1.2.0.3 plaintext, exported 2026-09-09, SHA-256 `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`. R3 recomputed the digest and confirmed 423 `.exp` sections plus the archive README, with no unsafe paths or symlinks. Primary implementation/source-compatibility evidence. |
| `SRC-002` | `README.md` inside `SRC-001` | OBSERVATIONAL | Accessible inside `sources/CoUnitPlaintextExport.zip`; records provenance and the four source findings recovered during export. |
| `SRC-003` | CODESYS Forge CoUnit tutorial/API/home | SUPPORTING | Public usage model: extend `FB_TestSuite`, use the test functions/assertions, run from a test task, inspect Device Log/xUnit. Web-accessible when network use is allowed; not project authority. |
| `SRC-004` | CoUnit CODESYS Forge repository, trunk/branch around v1.2 | HISTORICAL | CoUnit/TcUnit lineage and v1.2-era structure. Supporting only. |
| `SRC-005` | TcUnit 1.2.0.0 release, tag `df90ead` | SUPPORTING | Historical baseline near the apparent CoUnit fork. |
| `SRC-006` | TcUnit 1.3.0.0 release, tag `1577b79` | SUPPORTING | Defect/fix list for assertion types, bounds, sequential execution, named finish and whitespace. |
| `SRC-007` | TcUnit 1.3.1 release, tag `fac42a5` | SUPPORTING | Latest tagged TcUnit release confirmed by reviewer web check on 2026-09-09. |
| `SRC-008` | Current TcUnit `FB_AssertResultStatic` on `master` | SUPPORTING / VOLATILE | R1 observed current value-based assertion de-duplication. Reinspect before relying on current-master detail. |
| `SRC-009` | Current TcUnit `FB_TestSuite` on `master` | SUPPORTING / VOLATILE | R1 observed registration/order/test logic. Reinspect before relying on current-master detail. |
| `SRC-010` | Current TcUnit `FB_TcUnitRunner` on `master` | SUPPORTING / VOLATILE | R1 observed current runner/sequential-state logic. Reinspect before relying on current-master detail. |
| `SRC-011` | TcUnit issue #237 | SUPPORTING | STRING assertion history can be reinterpreted as REAL and fault. |
| `SRC-012` | TcUnit issue #266 | SUPPORTING | Disabled/ignored ordered tests can prevent later tests from running. |
| `SRC-013` | TcUnit issue #273 | SUPPORTING | REAL assertion can fault on NaN. |
| `SRC-014` | TcUnit PR #252 | SUPPORTING | xUnit XML escaping work. |
| `SRC-015` | TcUnit PR #268 | SUPPORTING | xUnit streaming/flush work. |
| `SRC-016` | CoUnit `JUnitv5.xsd` / Forge history | SUPPORTING | Intended JUnit-style result concepts and counts. The supplied `SRC-001` contains no `.xsd`; recover schema bytes separately from a stable source only when schema-specific qualification needs them. |
| `SRC-017` | R1 supplied architecture-stage instructions, `Pasted text(20260909-230427).txt` | CONTROLLING (R1 claim) | R1 records SHA-256 `6495c55aa3021d88c6bfda41040f6abc7a73bfd41c93b964f200e40d7a12c281`. The current review separately recovered the named v4 synthesizer contract; it did not prove byte identity with R1's pasted file. |
| `SRC-018` | TcUnit PR #274 | SUPPORTING | R1 observed proposed NaN handling: assertion outcome rather than runtime fault, any NaN unequal. |
| `SRC-019` | `03-blueprint-architecture-design-package-synthesizer-prompt-v4.md`, version 4, set `harmonized-v4`, 2026-09-08 | CONTROLLING | Exact governing authoring edition recovered during this review. It governs R2 package/handoff conformance, not CoUnit product intent. |

## Missing controlling input

The original project-specific CoUnit rebaseline assignment/delegation is not reconstructed. That gap no longer blocks this successor because `SRC-020` records the architecture owner's explicit 2026-09-09 approval of R2 and acceptance of the recommended `OPEN-COU-008` closure. R3 binds operative authority to that approval rather than claiming recovered historical delegation.

## Web locators retained from R1

- CoUnit tutorial: https://forge.codesys.com/lib/counit/tutorial/Tutorial/
- CoUnit API: https://forge.codesys.com/lib/counit/apireference/
- CoUnit repository: https://forge.codesys.com/lib/counit/code/HEAD/tree/trunk/coUnit
- TcUnit releases: https://github.com/tcunit/TcUnit/releases
- TcUnit repository: https://github.com/tcunit/TcUnit
- TcUnit issue #237: https://github.com/tcunit/TcUnit/issues/237
- TcUnit issue #266: https://github.com/tcunit/TcUnit/issues/266
- TcUnit issue #273: https://github.com/tcunit/TcUnit/issues/273
- TcUnit PR #252: https://github.com/tcunit/TcUnit/pull/252
- TcUnit PR #268: https://github.com/tcunit/TcUnit/pull/268
- TcUnit PR #274: https://github.com/tcunit/TcUnit/pull/274

Outside web checks in the R2 review only tested public/supporting facts; at that stage they did not fill the missing project intent, source archive, delegation or native CODESYS evidence. R3 closes the source and operative-authority gaps through `SRC-001` and `SRC-020`; native CODESYS evidence remains future qualification.

## R3 approval source

| ID | Source | Class | Binding, availability and use |
|---|---|---|---|
| `SRC-020` | 2026-09-09 architecture-owner instruction in the review session | CONTROLLING | The owner states that R2 is acceptable and accepts the reviewer's recommended closure of `OPEN-COU-008`. R3 uses this as explicit approval of the unchanged R2 choices and `ADR-COU-017`; it does not claim this recreates the missing historical assignment. |
