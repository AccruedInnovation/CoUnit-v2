# Installed CoUnit upgrade consumers

`qualification/upgrade_native_consumers.py` generates selected-row, lifecycle, helper, capacity and setup-error qualification suites with their callback/helper POUs in the sparse consumer at `..\consumer`. The script checks each suite's literal `Describe` metadata with `tools/controlled_boot.py`'s catalog parser. It does not contact an IDE, PLC, bridge, or runtime.

The fixed expected outcomes are written before any execution to `PlaintextExport/Tests/Upgrade/expected-native-consumers.json` and mirrored beside each suite as `expected-outcomes.json`. The values are fixture expectations authored in the generator; they are not derived from XML or JSON reports. `--xml-output` optionally writes one PLCOpenXML import package using the existing repository writer for the selected task-owned POUs.

Generate source, expected JSON, and an offline import package with:

```powershell
python qualification/upgrade_native_consumers.py `
  --consumer-root '..\consumer' `
  --xml-output "$env:TEMP\native-upgrade-consumers.xml"
```

The matched `tools/controlled_boot.py` adapter accepts an exact literal case/row or all matching rows. These are the stable selectors:

| Suite ID | Case ID | Row key | Expected run result | Expected case result |
|---|---|---|---|---|
| `upgrade.lifecycle` | `late-error` | `run` | `FRAMEWORK_ERROR`, nonempty termination reason | `PASSED`, zero failures and errors; late unbound assertion remains run-only |
| `upgrade.lifecycle` | `assert-then-error` | `run` | `FRAMEWORK_ERROR`, nonempty termination reason | `ERROR`; first BOOL failure retains `upgrade/lifecycle/original`, expected `expected-value`, actual `actual-value` |
| `upgrade.lifecycle` | `cleanup-failure` | `run` | `NORMAL` | `ERROR`; body failure remains first, fixture cause `BODY_FAILED` (2), cleanup `FAILED` (3) |
| `upgrade.lifecycle` | `cleanup-incomplete` | `run` | `NORMAL` | `ERROR`; body failure remains first, fixture cause `BODY_FAILED` (2), cleanup `INCOMPLETE` (4) after the five-second cleanup budget |
| `upgrade.lifecycle` | `cancel-timeout` | `run` | `ABORTED`, nonempty termination reason | `ABORTED`; body callback stays pending until an owner cancel or the configured 60-second run deadline requests cancellation, then cleanup passes and releases the test-owned resource |
| `upgrade.helper-oracle` | `helper-oracle` | `oracle` | `NORMAL` | `PASSED` only when converted helper oracle reports `Done=TRUE`, `OraclePass=TRUE`, `FailedCheck=0` |
| `upgrade.memory` | `memory-profile` | `size` | `NORMAL` | Deliberate `FAILED` diagnostic containing the three nonzero native `SIZEOF` measurements |
| `upgrade-assertions` | `assertion` | `custom` | `NORMAL` | One deliberate `FAILED` assertion, `domain/limit`, `Expected: limit=10`, `Actual: limit=12` |
| `upgrade-assertions` | `assertion` | `float` | `NORMAL` | One deliberate `FAILED` assertion for adjacent finite `REAL` bits `3F800000` vs `3F800001`, with `Delta=0` |
| `upgrade-assertions` | `assertion` | `string` | `NORMAL` | One deliberate `FAILED` long-string comparison; mismatch at byte/code-unit 299 in a 300-character value |

To inspect static inventory for a single row without invoking the boot route, use:

```powershell
python tools/controlled_boot.py `
  --suite-source '..\consumer\PlaintextExport\Tests\Upgrade\FB_UpgradeLifecycle' `
  --case-id late-error --row-key run `
  --inventory-output "$env:TEMP\late-error-inventory.json"
```

`FB_UpgradeLifecycle` owns a separate `CoUnit.I_CoUnitFixture` callback. Its body assertion is recorded once while the fixture phase is BODY; cleanup state is reported as PENDING and then terminal before `TEST_FINISHED`. `FB_UpgradeHelperOracle` contains only the converted deterministic qualification program and its local `FB_UpgradeCallback`; it references CoUnit APIs through the installed `CoUnit` namespace without importing library objects. `FB_UpgradeMemory` intentionally fails so the native profile's snapshot, suite, and runner sizes remain observable as a qualification diagnostic. `FB_UpgradeAssertions` is copied from the canonical generated `upgrade_assertions/FB_UpgradeAssertions` sources. Its inherited base, completion calls, and retained `MEMCPY` function are qualified through `CoUnit`; its methods, counters, handles, and three deliberate assertion semantics are otherwise unchanged.

The separate live fixture includes the guarded-completion sibling; live binding/control qualification remains open. No host command here claims dynamic host-side discovery, polling, or cancellation: row execution remains the existing boot-bundle invocation, with its current one-shot run lifecycle.
