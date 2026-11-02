# Stable catalog and controlled run example

`FB_TestSuite` catalogs keep stable case identity separate from the display name. Override `Describe` (or bounded `DescribeNext`) to set the suite ID once and declare each case with `DefineCase(CaseId, Name, RowKey, Tags, Disabled)`. Save the returned `UINT` handles in suite-owned fields. `Describe` is declaration-only: do not perform setup or mutate a DUT there.

Each cyclic suite body uses `IF BeginCase(Handle := handle) THEN` to guard all effects and assertions for that row. Call `TEST_FINISHED()` when the row is complete. A selected multi-scan case may call `BeginCase` again on later scans while preserving suite-owned progress. Disabled cases remain listed. Deselected rows carry Selected=FALSE and become SKIPPED at selection freeze; neither they nor disabled rows may produce effects.

## Two parameter rows

Create `FB_GainCases` with this declaration:

```iecst
FUNCTION_BLOCK FB_GainCases EXTENDS CoUnit.FB_TestSuite
VAR
	_low : UINT;
	_high : UINT;
	_expected : DINT;
	_actual : DINT;
END_VAR
```

Add an override method named `Describe`. Its declaration and implementation are:

```iecst
METHOD Describe
VAR
	_ok : BOOL;
END_VAR
```

```iecst
_ok := SetCatalogIdentity(SuiteId := 'example.gain');
_low := DefineCase(CaseId := 'gain', Name := 'Low', RowKey := 'low', Tags := 'smoke', Disabled := FALSE);
_high := DefineCase(CaseId := 'gain', Name := 'High', RowKey := 'high', Tags := 'smoke', Disabled := FALSE);
```

The FB implementation is:

```iecst
IF BeginCase(Handle := _low) THEN
	_expected := 20;
	_actual := 10 * 2; // Replace with the DUT call for this parameter row.
	AssertEquals_DINT(Expected := _expected, Actual := _actual, Message := 'low gain');
	CoUnit.TEST_FINISHED();
END_IF
IF BeginCase(Handle := _high) THEN
	_expected := 40;
	_actual := 20 * 2;
	AssertEquals_DINT(Expected := _expected, Actual := _actual, Message := 'high gain');
	CoUnit.TEST_FINISHED();
END_IF
```

Instantiate it persistently in the program that calls `RUN_CONTROLLED`. After
Configure reaches `CatalogReady`, operation 2 with `SuiteId='example.gain'`,
`CaseId='gain'`, `RowKey='high'`, then operation 3 with `ExpectedSelected=1`
runs only High; Low remains in the catalog and is skipped. Supply the configured
RunId/current generation and a fresh increasing RequestId for each command.
For large catalogs use `DescribeNext` as described in the [user guide](../2.1-upgrade.md#catalog-preparation-and-capacity).

## Public controlled exchange

The application owns one `ST_CoUnitExchange` and calls `RUN_CONTROLLED(Exchange := Exchange)` exactly once each scan from one task. For each command, populate the payload first, then write a strictly increasing `RequestId` last. Wait for `AckId = RequestId` before changing the payload.

The public command sequence is:

1. **Configure/list** with operation `1`, setting unique `RunId`, `BuildId`, `TargetId`, and positive `RunTimeout` and `CleanupTimeout`. ACK accepts configuration; wait for `Status.CatalogReady` before selecting, paging or starting. Catalog preparation runs on later owner scans without bodies/setup, then freezes the completed catalog; initially all cases are selected.
2. **Select** with operation `2`, `RunId`, `ExpectedGeneration`, and optional suite/case/row/tag selectors. This replaces the selection and remains available only before start.
3. **Start** with operation `3` and `ExpectedSelected`. Set `AllowEmpty` only when an empty run is intentional.
4. **Cancel** with operation `4` while the run is active.
5. **Read one descriptor/result page** with operation `5` and one-based `SuiteIndex` / `CaseIndex`.

Check the acknowledgement, public status, descriptor identity, selected inventory, terminal state, assertion count, and first failure separately. A rejected stale request must not change the completed run truth. Keep the cyclic call active while publication and cleanup finish.

`ExpectedSelected` counts every matching descriptor, including selected disabled
rows. For example, selecting the whole three-row guard suite means three selected,
two started bodies and one disabled skip. This differs from both capacity and
assertion counts; use the actual frozen selection as the Start oracle.

The native fixture in `qualification/upgrade_core.py` demonstrates a configure/list before execution, row selection, one disabled sibling, a three-scan body, public result paging, and a post-completion stale cancel. Its `expected.json` is an independent acceptance oracle; the PLC program's output flags do not constitute native evidence until the chosen runtime produces a fresh observed run.

## Legacy guarded tests and strict definitions

For incremental migration, `TEST_GUARDED(name)` gates all body effects and DUT calls. Disabled names return false, completed names return false on later scans, and an active sibling remains executable. Once the suite declares strict cases, undeclared or duplicate test definitions are framework errors. See the `upgrade_legacy` and `upgrade_strict_*` packages emitted by `qualification/upgrade_core.py`.

## Reporting assertion examples

Use `AssertResult` for a domain assertion with a stable `CheckId`, message, expected/actual text, and bounded detail. Use typed `REAL`/`LREAL` assertions for numeric tolerance checks. The `upgrade_assertions` fixture checks a custom assertion, adjacent finite `REAL` values with zero tolerance and exact raw-bit/delta diagnostics, and a long `STRING(300)` mismatch near the last code unit.
