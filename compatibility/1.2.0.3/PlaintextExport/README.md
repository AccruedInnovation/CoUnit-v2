# Patched CoUnit source snapshot

`1.2.0.3/PlaintextExport` contains the textual declarations and implementations read from:

`C:\ProgramData\CODESYS\Managed Libraries\www.co5e.org\coUnit - A unittest framework for CODESYS\1.2.0.3\counit_revised.library`

Exported on 2026-09-09 by opening the library as a secondary CODESYS project through MCP. The primary test project remained open. All 423 text sections were written beneath this explicit destination and compared with the readback. Object hierarchy is preserved; each textual object has its own directory and `.DEC.exp` / `.IMP.exp` files. This is a source-analysis snapshot, not a complete native-project replacement: library references, project settings and project information remain in the original `.library`.

The repository's `CodesysGitExport.py` was not executed or modified: its current `save_folder` points at the main `repo/PlaintextExport`, and its export-only filter selects a specific motor object. Do not run that script against this library without explicitly overriding and verifying both settings.

## Findings from this snapshot

- `FB_coUnitRunner.RunTestSuiteTests` invokes registered suite bodies after setting `CurrentTestSuiteBeingCalled`. Calling suite bodies separately before `CoUnit.RUN()` executes them without that context and can register tests under another suite. The control runner now lets CoUnit own invocation.
- `FB_AssertResultStatic.ReportResult` has no search loop assigning `FoundOne` or `AdditionalIdenticalAssert`. Every accepted invocation therefore appends an assertion. Its final assignment updates `CurrentCycleCount`, not the stored `CycleCount`.
- `FB_AssertResultStatic.AddAssertResult` increments `TotalAsserts` and indexes the array without checking its 2,048-entry capacity. Repeated assertions can therefore overrun storage. This is a concrete defect; the exact earlier simulator exception has not yet been reproduced with an observed overflowing index.
- `FB_xUnitXmlPublisher.LogTestSuiteResults` writes `NumberOfSuccessfulTestCases` into the root `tests` attribute. A run with 56 cases and four failures therefore reports `tests="52"` at the root. Count and reconcile individual cases and suite totals rather than trusting that attribute.

These library defects are documented, not patched in the installed dependency. The snapshot retains the original code for review.
