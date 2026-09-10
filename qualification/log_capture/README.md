# Native log event observer (test only)

Import `observer.xml` alongside the candidate and a qualification fixture into the disposable native project. It registers `CmpLog.EventIDs.EVT_LogAdd` through the documented `CmpEventMgr` function callback API, filtering the exact component identifier used by `Support/CmpCfLog`. The callback resolves `EVTPARAM_CmpLogAdd.pszInfo` and its native argument list using `CmpLog.LogCopyInfo`; it never adds a log entry or changes framework truth.

This observer requires **an explicit CmpLog 3.5.21 reference under namespace `CmpLog`, and a runtime exporting `LogCopyInfo`**, qualified in the disposable project. Temporarily replace the older `#CmpLog` placeholder for observer tests, then restore the candidate's original placeholder/reference from the native candidate template. Parallel old/new references under a separate namespace did not expose the resolver to the native compiler; do not use that configuration. This qualification-only binding is not a shipping dependency change. Record it separately from ordinary candidate runs.

The older event declaration's `pargList : POINTER TO STRING` does not mean that it points directly to the text. The native `device-log-native2.json` attempt captured nine `%s` format strings, not the displayed messages. [CODESYS SP21 release note CDS-63087](https://api-www.codesys.com/fileadmin/user_upload/CODESYS_Group/Ecosystem/Up-to-Date/Releases-Lifecycle/Release-Updates/Release-Notes/Release-Notes-CODESYS-35210.html) requires the new resolver for complete event text. Its [documented signature](https://content.helpme-codesys.com/en/libs/CmpLog/Current/LogCopyInfo.html) owns argument-list interpretation and accepts the destination byte capacity. No guessed `va_list` or pointer-to-pointer decoding is used here.

For fixtures exposing `PRG_Qualification.Done` and `.OraclePass`, import `wrapper.xml` and schedule **only `PRG_QualificationObserved`**, replacing the normal fixture task call. Otherwise call `F_QualificationLogStart()` before fixture actions and `F_QualificationLogStop()` after their completion. A different component identifier can be supplied to `F_QualificationLogStart(ComponentFilter := ...)`.

`PRG_QualificationObserved.WaitForReport` defaults to `FALSE`, retaining the fixture's ordinary completion predicate. Set it to `TRUE` before the first wrapper call when publication logs must also be captured. The wrapper continues calling the fixture after its `Done` until the runner's publisher reaches `WRITTEN`, `FAILED`, or `DISABLED`, then unregisters/closes. The fixture must continue servicing its runner on those later calls; the wrapper does not independently invoke it a second time.

Read `GVL_QualificationLog` after `Stop` succeeds:

- `Count` commits complete entries in order, bounded to 128.
- `Bytes[entry, 0..Lengths[entry]-1]` is the byte-exact oracle. Use these bytes for UTF-8 fixtures even when the native project is in legacy STRING mode.
- `HexEntries[entry]` contains the same bytes as lowercase ASCII hex, materialized after unregistering in `Stop`; reading one string per entry avoids slow per-byte native host calls.
- `Entries` is a display convenience; `Classes` preserves log class IDs.
- `Overflow`, `Truncated`, or `CallbackErrors > 0` invalidates claims about complete captured content, including absence of success messages.
- `LastCopyError` records resolver failure. `ERR_BUFFERSIZE` marks truncation; other resolver errors invalidate capture through `CallbackErrors`.
- `StartError`, `UnregisterError`, and `CloseError` expose native registration/cleanup outcomes. `Registered` and `EventHandle` remain available when cleanup fails. Do not unload callback code with `Registered=TRUE`; call `Stop` again after addressing the failure.

The observer is for isolated, single-owner-task CoUnit fixtures. Other runtime components are filtered out. Do not enable concurrent writers using the same CoUnit component during capture. Neither the observer nor the wrapper infers semantic log correctness from a successful API return: compare captured bytes with fixture expected messages and reject unexpected success banners in failure cases.

Generate with `python generate.py`; `--check` verifies checked-in plaintext regeneration. Native compilation, event delivery, component filtering, and cleanup must be verified in the disposable simulator project. These objects are outside production `PlaintextExport` and must not ship with CoUnit.
