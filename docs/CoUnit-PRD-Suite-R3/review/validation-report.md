# CoUnit PRD Suite R3 validation report

**Subject:** `COUNIT-PRD-SUITE-R3`, successor to the reviewed `COUNIT-PRD-SUITE-R2`.  
**Architecture:** unchanged `COUNIT-ARCH-R3` / `2026-09-09-r3`.  
**Validation type:** author-time structure, reference, source binding, contract controls, artifact shape, analytical path boundary, and host xUnit oracle checks.  
**Scope limit:** this is not native CODESYS runtime proof, fresh-recipient evidence, implementation acceptance, or release qualification.

## Result

`PASS` for the checks that can run in the supplied document/source workspace.

Final packet checker output:

```text
PASS
PRDs: 4; slices: 12; assertion methods: 44; compatibility surface rows: 60
SRC-001 sha256: 458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48
SRC-001 entries: 665
R14 path-byte controls: UTF8 122×U+00E9=244 bytes accepted-boundary; 123×U+00E9=246 bytes rejected-boundary
runtime matrix row widths: 27 fields
xUnit controls: positive=0; negatives=3 rejected
```

Raw output is retained in `validation-raw.txt`.

## Commands actually run

From the R3 delivery root:

```text
python -m py_compile review/validate_packet.py PRD-COU-04/tools/verify_xunit.py
python review/validate_packet.py
python PRD-COU-04/tools/verify_xunit.py PRD-COU-04/fixtures/xunit/mixed-results.xml PRD-COU-04/fixtures/xunit/mixed-results.expected.json
```

The three negative xUnit fixtures were also run separately with the same verifier and were required to return nonzero:

- `bad-count.xml` — rejected for root count mismatch;
- `bad-terminal.xml` — rejected because one testcase has multiple terminal result children;
- `bad-assertions.xml` — rejected because `assertions` is negative.

CSV rows were read independently with Python's standard CSV parser to compare row widths. The final widths are:

- assertion-family map: 3 fields per row;
- public API surface: 5 fields per row;
- defect-to-verification map: 5 fields per row;
- runtime matrix: 27 fields per row, including header and template data row.

Each main PRD was also checked to have headings `1..13` in exact order and exactly 21 implementability-matrix rows.

## R3 controls added by this review

### RF-008 path byte-capacity control

The validator now checks the R3 rule and runs the analytical boundary used by `R14-path-byte-capacity`:

- 122 × U+00E9 encodes to 244 UTF-8 content bytes; adding either 11-byte reserved suffix reaches the 255-byte boundary and is admissible;
- 123 × U+00E9 encodes to 246 bytes; adding a suffix would need 257 bytes and must be rejected before file effect.

The check also requires the R3 path obligation/test markers in the canonical PRD and no longer accepts the superseded character-count capacity rule in active product-design material.

### RF-009 legacy mapping control

The validator requires `legacy_mapping_id` in the runtime matrix and enforces:

- `UTF8` => `legacy_mapping_id=N/A`;
- `LEGACY_SINGLE_BYTE` => a nonempty, non-`UNBOUND`, non-`N/A` mapping ID before support may be claimed;
- an unbound encoding profile may not claim a mapping.

The PRD/qualification contract and S2 handoff also require a mapping-sensitive raw-byte case whose expected logical Unicode result comes from retained compiler/runtime mapping evidence rather than the PLC converter under test.

### RF-010 CSV-width control

The R2 probe found 26 header fields and 29 data fields in `runtime-matrix.csv`. The R3 validator now parses raw CSV rows first and rejects any row whose cell count differs from the header. The R3 matrix is 27/27 after adding the mapping column and quoting free text correctly.

## Regression controls retained

The packet checker also rechecks the major R2 controls that close historical `RF-001..007`:

- four PRDs preserve the exact v4 13-heading order and 21-row matrix;
- all four end `Implementation-ready: no` and all 12 slices remain `NOT_READY`;
- exact embedded `SRC-001` digest matches and its archive contains no absolute or parent-traversal paths;
- assertion-family map contains the exact 44-method surface;
- public compatibility map contains the exact 60 R3-preserved surfaces and recomputed source hashes/normalized declarations match `SRC-001`;
- ordered-registration terminal skip rule remains present;
- raw-bit FP special-value classification remains present;
- byte-bounded diagnostic/string rules remain present;
- encoding-aware XML rules remain present;
- snapshot memory qualification remains present;
- support disposition remains non-averaging over required focused, all-VER, and integrated-scenario evidence;
- positive xUnit fixture is accepted and all three semantic negative controls are rejected.

## xUnit positive observation

The positive host fixture parses as 4 tests with one pass, one failure, one skipped case, and one framework error. The verifier checks aggregate counts, terminal child uniqueness, nonnegative `assertions`, and the supplied failure/error details. This proves only the supplied host oracle/fixture relationship; it has not yet parsed a PLC-produced R3 report.

## Checks deliberately not claimed

- active implementation repository/candidate/local diff binding;
- CODESYS native compile or runtime execution;
- target task/atomic behavior;
- target SysFile open/write/flush/close/rename/delete and fault behavior;
- target companion-path helper behavior;
- compiled snapshot size and application memory budget;
- exact target legacy byte mapping and mapping-sensitive PLC XML result;
- real downstream current CoUnit consumer compile;
- actual PLC-generated xUnit parse;
- complete runtime/support matrix execution;
- fresh packet-only recipient review;
- target-worker implementation trial;
- implementation acceptance or release/runtime support.

Those gaps remain represented by the PRDs' `PARTIAL` state and slice `NOT_READY` gates. No unrun future product test is relabeled as a failed author-time design check.
