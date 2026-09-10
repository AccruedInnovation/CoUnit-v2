# Changelog

## 2026-09-09 — R3 source/authority/assertion closure

- Packaged the exact `SRC-001` source at `sources/CoUnitPlaintextExport.zip`; SHA-256 matches the R1/R2 identity exactly.
- Recorded `SRC-020` explicit architecture-owner approval of the R2 basis and accepted `OPEN-COU-008` closure.
- Added approved `ADR-COU-017`: remove persistent per-assertion identity/history; evaluate every assertion; log detailed assertion failure only on the first-failure transition; define `NumberOfAsserts` as maximum assertion calls observed in any single test-body invocation; retain `MaxNumberOfAssertsForEachTestSuite` as a hard per-suite-body-invocation call bound.
- Closed `OPEN-COU-006`, `OPEN-COU-007`, and `OPEN-COU-008` as `FIXED_AND_RECHECKED` at architecture level.
- Updated `IF-COU-003`, `ISC-COU-002`, requirements, QAS/FE, branch-changing scenario/oracle, PRD allocations and handoffs.
- Corrected the R2 assumption that `SRC-001` contains a local JUnit XSD; schema-specific checks must retrieve `SRC-016` separately if needed.
- Raised package completeness to `COMPLETE`, approval to `APPROVED`, and all four assignments to `READY_FOR_PRD`.

## 2026-09-09 — R2 adversarial repair

- Reviewed unchanged `COUNIT-ARCH-R1` before edits.
- Lowered package completeness from `COMPLETE` to `BLOCKED` because the exact `SRC-001` authoring source and project-specific authority source are not accessible from the handoff.
- Marked `ADR-COU-007` contradicted: `(test index, assertion ordinal)` can alias distinct assertion statements when multi-scan control flow changes.
- Added a shared external report-currentness invariant and interruption/restart acceptance case.
- Added explicit cross-PRD contribution boundaries for `REQ-COU-001`, `REQ-COU-004`, and `REQ-COU-031` plus `ISC-COU-004`.
- Corrected PRD fixed references, dependency gates, reading routes, `QAS-COU-011` omission, and readiness projections.
- Added review findings `RF-COU-001..006`, R2 gates, and successor recheck evidence.

## 2026-09-09 — R1

- Initial CoUnit architecture rebaseline candidate.
