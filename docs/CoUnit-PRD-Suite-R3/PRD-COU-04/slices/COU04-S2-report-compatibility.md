# COU04-S2 — Report oracle, currentness harness, and source-compatibility cohort

**Parent:** `PRD-COU-04`  
**Status:** `NOT_READY`  
**Reason:** accepted candidate, active repository, native downstream compile cohort, and fresh recipient check are not yet bound.

## Outcome and allocation

Implement qualification material for `VER-COU-019..024` and `031`: independent xUnit parsing, large-report checks, controlled I/O/currentness faults, inherited-defect regression, and real public-API source compatibility.

## Required reading — read now

1. `../PRD.md` §§1, 4–6, 9–11;
2. `../contracts/qualification-contract.md` §§1–4, 6–8;
3. accepted `PRD-COU-03/contracts/reporting-contract.md`;
5. `../tools/verify_xunit.py` and `../fixtures/xunit/*`;
6. `../qualification/public-api-surface.csv`.

## Reference inventory

- host XML verifier + static fixtures: `SUPPLIED_WITH_PRD`; author-time positive and negative checks already ran.
- exact current public source surface: `SUPPLIED_WITH_PRD` CSV derived from `SRC-001`.
- accepted candidate report publisher: `PRODUCED_BY_PREDECESSOR` PRD-03.
- real current downstream project(s): `EXISTING` only after qualification owner binds exact project/revision; currently unavailable.
- target filesystem fault method: qualification worker selects a safe target-supported injection method without changing expected currentness semantics.

## Settled design and steps

1. Run PLC-generated xUnit reports through an independent XML parser. Compare parsed case terminals and counts to a separately captured canonical final snapshot/test expectation.
2. Escape/encoding cases must include XML metacharacters plus non-ASCII text under each claimed project `STRING` encoding mode. UTF-8 mode must prove no legacy double-transcoding; malformed UTF-8/replacement behavior is exercised where the native fixture can construct those bytes. For every claimed `LEGACY_SINGLE_BYTE` profile, bind `legacy_mapping_id` from independent compiler/runtime evidence and include raw bytes whose decoded result is mapping-sensitive. At minimum exercise `0x80` and `0xE9` when those bytes are representable: compare PLC XML text with the externally established mapping result, applying the PRD-03 XML-forbidden-code-point replacement rule. Do not derive the expected result from the PLC converter under test.
3. Run the PRD-03 path-capacity boundary before filesystem fault work: ASCII 244 bytes and UTF-8 122 × U+00E9 (244 bytes) are admissible; ASCII 245 bytes and UTF-8 123 × U+00E9 (246 bytes) must fail before any file adapter effect. Assert accepted `stage`/`backup` paths are exactly 11 bytes longer and pairwise distinct.
4. Large report must exceed the configured publisher chunk by a clear margin while remaining within test-environment storage capacity; parser must consume the complete final file and count all cases.
5. For each target-supported pre-commit fault point—stale-stage cleanup, backup prep, stage open, write/short write, flush, close, stage->final rename—assert publisher `FAILED`, no success banner, test truth unchanged, and the final path names the prior complete report or no report as required.
6. Reinitialize after stage bytes exist but before semantic commit. On next publication startup, assert stale staging is non-current and recovery follows PRD-03 startup rules.
7. Post-commit backup-delete failure is a warning case: final complete report remains current and publication remains `WRITTEN`.
8. Compare candidate declarations to the 60-row R3-preserved `public-api-surface.csv`, including `TEST_ORDERED`, `FB_TestSuite`, `I_TestResults`/methods, legacy result DUTs, `E_AssertionType`, and `GVL_Param_coUnit`; report differences for review rather than silently updating the baseline.
9. Compile at least one real downstream project that already uses current CoUnit source/API with no normal test-source edits. This is mandatory before `VER-COU-023` passes. A generated compile fixture is supplementary only.
10. Run the exact inherited regression cases represented by `defect-to-verification-map.csv`; do not accept a local pass when the spanning currentness/result truth scenario fails.

## Safety/effects

Filesystem fault work must run only in a disposable test directory on a permitted target. Do not use production-control paths or real CI report locations. Pre-create a known prior report with a unique sentinel and verify its bytes after each failed path.

## Exit gate

- host parser works on actual PLC output and the author-time controls reject deliberately wrong counts, multiple terminal children, and invalid assertion-count attributes;
- every claimed legacy row has exact mapping evidence and a mapping-sensitive raw-byte XML case;
- path-capacity boundary cases prove byte-based rejection before effects and exact distinct companions at the accepted boundary;
- currentness fault evidence exists for every supported injection point, with unsupported fault injection marked `INCONCLUSIVE` rather than skipped-as-pass;
- real downstream compile cohort is identified and compilation result retained;
- `VER-COU-019..024` and `031` each have an evidence path and honest status.
