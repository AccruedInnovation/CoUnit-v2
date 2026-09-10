# CoUnit 1.2.0.3 source observations used by the PRDs

**Canonical source:** `../architecture/sources/CoUnitPlaintextExport.zip` (`SRC-001`, SHA-256 `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`).  
**Observation basis:** plaintext export packaged by `COUNIT-ARCH-R3`. The source README states that it is a source-analysis snapshot, not a full native CODESYS `.library` with all project settings/library references. These observations describe the supplied baseline; they do not prove runtime behavior on a target.

| Area | Existing object/path in the source export | Observed baseline behavior relevant to design |
|---|---|---|
| Runner | `Unit Test Framework for CODESYS/POUs/FB_coUnitRunner/RunTestSuiteTests/RunTestSuiteTests.IMP.exp` | Uses global suite registry, temporary finished-suite counting, directly invokes suite FBs, then continuously asks result/log/xUnit objects to progress. |
| Sequence runner | `.../FB_coUnitRunner/RunTestSuiteTestsInSequence/RunTestSuiteTestsInSequence.IMP.exp` | Uses `CurrentlyRunningTestSuite`, `TOF`, and a temporary finished count; terminal handling depends on counter/suite-index conditions. |
| Suite storage | `.../FB_TestSuite/FB_TestSuite.DEC.exp` | Fixed `Tests[]`, duplicate trigger/cycle arrays, scalar and array assertion tracker FBs, and `FirstCycle` state. |
| Test registration | `.../FB_TestSuite/AddTest/AddTest.IMP.exp` | Trims names; detects leading `disabled_` case-insensitively; uses task cycle count as duplicate identity; scans by `NumberOfTests`; writes new test storage. |
| Public test facade | `.../POUs/Functions/TEST`, `TEST_ORDERED`, `TEST_FINISHED`, `TEST_FINISHED_NAMED`, `IS_TEST_FINISHED` | Uses shared globals for current suite/name and directly traverses suite storage. Named finish can abort on unknown name; `IS_TEST_FINISHED` assumes the current suite pointer is valid. |
| Task lookup | `Support/POUs/GetCurTaskInfo/GetCurTaskInfo.IMP.exp` | Calls `IECTaskGetCurrent`/`IECTaskGetInfo3` and dereferences the returned task-info pointer without a complete failure guard. |
| Assertion trackers | `.../FB_AssertResultStatic`, `FB_AssertArrayResultStatic` | Retain assertion-result/cycle histories. `ReportResult` contains declared search-result flags that are not assigned in the supplied implementation; add methods increment and index bounded arrays without the R3 pre-write guard. |
| Test failure record | `.../FB_TestSuite/SetTestFailed/SetTestFailed.IMP.exp`, `.../FB_Test/FB_Test.DEC.exp` | A test stores one failed flag, one assertion type, and one assertion message; later failures overwrite the fields today. |
| Assertion API | 44 public `Assert*` methods under `.../FB_TestSuite/` | Public scalar, `ANY`, 1-D array, 2-D REAL/LREAL, and 3-D REAL/LREAL families exist; `PRD-COU-02/contracts/assertion-family-map.csv` records their exact exported signatures. |
| Limits | `.../GVLs/GVL_Param_coUnit/GVL_Param_coUnit.DEC.exp` | Fixed suite/test/assertion limits are all `UINT`; source values are 32 suites, 2048 tests/suite, 2048 assertions/suite invocation; xUnit buffer is 1,048,576 bytes in this snapshot. |
| Legacy results | `.../DUTs/ST_TestCaseResult`, `ST_TestSuiteResult`, `ST_TestSuiteResults`; `.../FB_TestResults` | Legacy result types have pass/fail/skip-era fields and no distinct per-test framework-error state. Current result collection is incremental, and the current successful total does not model skipped/error/aborted as required by R3. |
| Device Log | `.../Functions/WRITE_DEVICE_LOG/WRITE_DEVICE_LOG.IMP.exp` | Returns without logging if `%s` is absent; messages over its local limit are emitted right part before left part. |
| xUnit | `.../FB_xUnitXmlPublisher/LogTestSuiteResults/LogTestSuiteResults.IMP.exp` | Builds an entire document in `FB_XmlControl`, writes the root `tests` attribute from successful-test count, then logs export success after `DeleteOpenWriteClose` without checking that helper's result. |
| File wrapper | `.../FB_FileControl` and `.../FB_xUnitXmlPublisher/DeleteOpenWriteClose` | Existing flow deletes the configured final path, opens it for write, writes the whole buffer, closes it. `FB_FileControl.Write` ignores the byte-count return from `SysFileWrite`. |
| String diagnostic bound | `Support/DUTs/T_MaxString/T_MaxString.DEC.exp` | `T_MaxString` is `STRING(255)`. |

## Source facts that remain unknown until repository/target binding

- Exact active implementation repository, storage form (`.library`, file-based storage, PLCOpenXML/native export, or other), branch/commit and local changes.
- Exact installed library references, compiler version, CODESYS Development System version, and target runtime/component versions.
- Exact target behavior of SysFile rename/flush/result codes and task APIs on supported release targets.
- Existing downstream user test projects suitable for the source-compatibility cohort; none are included in `SRC-001`.

These are dispatch/qualification inputs, not permission to change R3 semantics.
