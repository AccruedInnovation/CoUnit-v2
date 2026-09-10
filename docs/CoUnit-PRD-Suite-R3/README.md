# CoUnit PRD Suite R3

**Package:** `COUNIT-PRD-SUITE-R3`  
**Date:** 2026-09-09  
**Reviewed predecessor:** `COUNIT-PRD-SUITE-R2`, supplied archive SHA-256 `67d3f8f61027b1970e8c4a3b592327c0f1e19488a76eca3476c1be08482a19e9`  
**Architecture baseline:** `COUNIT-ARCH-R3` / `2026-09-09-r3` — `APPROVED`  
**Source baseline:** exact packaged CoUnit 1.2.0.3 plaintext source snapshot (`SRC-001`), SHA-256 `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`  
**PRD approval:** all four PRDs are `CANDIDATE`  
**Overall implementation-ready:** **no**

R3 is the repaired successor from a v4 adversarial review of R2. The review found three new defects: the report companion-path limit used character count for a byte-sized CODESYS `STRING`, legacy XML support evidence did not have to bind or distinguish the exact single-byte mapping, and the runtime-matrix CSV data row had more cells than its header while the validator still passed it.

The repairs remain within the approved R3 architecture. PRD-01 and PRD-02 remain revision R2 because no new defect required a controlling change. PRD-03 and PRD-04 advance to R3. Seven earlier R1 findings fixed in R2 remain closed and were checked for regression.

All four PRDs remain `PARTIAL`, and all 12 slices remain `NOT_READY`. The active implementation repository/candidate/toolchain is still unbound (`OPEN-COU-001`), and the mandatory fresh packet-only recipient review has not run. Later qualification also depends on accepted predecessor implementations, target CODESYS/runtime evidence, snapshot memory proof, exact legacy mapping evidence where legacy mode is claimed, a real downstream compatibility project, and the final release runtime matrix. No implementation, runtime support, or release approval is claimed.

## R3 adversarial-review result

New findings against unchanged R2:

- `RF-008` — `MAJOR`: report companion-path admission used `LEN` character count even though `STRING(255)` capacity is byte-based. R3 uses stored-byte admission, bounded suffix append, exact NUL/length/distinct checks, and no-effect over-limit cases.
- `RF-009` — `MAJOR`: legacy XML qualification could pass with only a broad `LEGACY_SINGLE_BYTE` label. R3 adds `legacy_mapping_id` and requires mapping-sensitive raw-byte evidence with an independent expected result.
- `RF-010` — `MODERATE`: runtime-matrix CSV header/data widths were 26/29 and the R2 validator missed the extra cells. R3 produces a 27/27 matrix and rejects width mismatch.

All three are `FIXED_AND_RECHECKED` at document/artifact level. See `review/prd-review.md` and `review/r2-probe-evidence.txt`.

## Reading routes

### Architecture/integration owner

1. this README;
2. `architecture/README.md` and `architecture/prd-authoring-assignments.md`;
3. each `PRD-COU-0N/PRD.md` §1 and §13;
4. `review/prd-review.md`, then `review/coverage.md`, `review/validation-report.md`, and `review/author-only-consumption.md`;
5. the detailed contract/slice only for the area being dispatched or checked.

### PRD-01 worker

Read `PRD-COU-01/PRD.md` §1, then the assigned slice and `contracts/execution-core-contract.md`. Use the exact R3 architecture/source references named by the slice.

### PRD-02 worker

Read `PRD-COU-02/PRD.md` §1, then the assigned slice and `contracts/assertion-engine-contract.md`. `contracts/assertion-family-map.csv` is the exact 44-method public assertion inventory.

### PRD-03 worker

Read `PRD-COU-03/PRD.md` §1, then the assigned slice and `contracts/reporting-contract.md`. XML/publication work also reads `review/platform-api-evidence.md`. For S2/S3, the stored-byte path rule and exact text-mode/mapping binding are mandatory.

### PRD-04 worker

Read `PRD-COU-04/PRD.md` §1, then the assigned slice and `contracts/qualification-contract.md`. S2 uses the supplied xUnit verifier/fixtures, exact 60-row public surface, path-byte boundary, and mapping-sensitive legacy case. S3 uses the runtime matrix and exact row support rule. Native qualification still waits on accepted PRD-01/02/03 outputs and real CODESYS target/tool access.

## PRD status and allocation

| PRD | Revision | Capability / architecture allocation | Detailed-design result | Dispatch |
|---|---|---|---|---|
| `PRD-COU-01` | `R2` | `CAP-COU-01`; `REQ-COU-001..006`, `009..014`, `031`, `033`, `035` | runner/suite/test/task lifecycle fixed | S1/S2/S3 `NOT_READY` |
| `PRD-COU-02` | `R2` | `CAP-COU-02`; `REQ-COU-001`, `004`, `007..008`, `015..021`, `034`, `037` | assertion count/outcome, scalar/ANY/array behavior fixed | S1/S2/S3 `NOT_READY` |
| `PRD-COU-03` | `R3` | `CAP-COU-03`; `REQ-COU-001`, `022..031`, `036` | final snapshot/log/XML/publication fixed; byte-safe companion paths; `OPEN-COU-003` closed | S1/S2/S3 `NOT_READY` |
| `PRD-COU-04` | `R3` | `CAP-COU-04`; `REQ-COU-032`; final verification of `REQ-COU-001..037` | qualification corpus/oracles/runtime evidence fixed; exact legacy mapping binding | S1/S2/S3 `NOT_READY` |

Cross-PRD allocations overlap where a shared obligation has several contributions. `architecture/verification-and-readiness.md` remains the canonical whole-architecture mapping.

## Detailed decisions retained and added

Retained from R2:

- PRD-01: one-way atomic `DWORD` cross-task violation latch; owner task alone mutates complex runner state.
- PRD-02: one assertion transaction per public assertion call; no persistent assertion identity; raw-bit special-FP classification and bounded diagnostic text.
- PRD-03: reserved sibling staging/backup paths; bounded streamed XML; restore-aware semantic commit/currentness; target memory feasibility gate.
- PRD-04: exact runtime rows, real downstream compatibility cohort, independent host XML oracle, and non-averaging final qualification.

Added in R3:

- `DD-COU03-006` / `L-COU03-007`: report companion paths are admitted by stored byte length and bounded append, not character count; overflow/truncation/alias is rejected before file effects.
- `DD-COU04-006` / `L-COU04-005`: legacy support rows bind the exact byte mapping and a mapping-sensitive independent raw-byte XML oracle.

These are local detailed-design/evidence repairs. They do not grant implementation or release approval.

## Artifact inventory

- `architecture/` — unchanged `COUNIT-ARCH-R3` package and exact source snapshot.
- `PRD-COU-01/PRD.md`, execution contract, and 3 worker slices.
- `PRD-COU-02/PRD.md`, assertion contract, exact 44-method assertion CSV, and 3 worker slices.
- `PRD-COU-03/PRD.md`, R3 reporting contract, and 3 worker slices.
- `PRD-COU-04/PRD.md`, R3 qualification contract, runtime matrix/schema, xUnit verifier and fixtures, public API inventory, defect map, and 3 worker slices.
- `review/prd-review.md` — current R2→R3 adversarial review and repair record.
- `review/r2-probe-evidence.txt` — unchanged-R2 counterexamples and CSV observation.
- `review/source-observations.md` — source observations used by the design.
- `review/platform-api-evidence.md` — CODESYS API/string/path support evidence; target qualification still required.
- `review/author-only-consumption.md` — all-slice same-context reconstruction, explicitly **not** fresh-recipient evidence.
- `review/coverage.md` — bounded local/boundary/integrated review coverage and limits.
- `review/validation-report.md` / `review/validation-raw.txt` — R3 author-time checks.
- `review/original-r1-*` — retained historical R1 validation evidence from the prior review; not current-candidate proof.

## Current gates

1. `OPEN-COU-001`: bind active repo/project, exact candidate/local changes, CODESYS toolchain/target, worker, writable scope, and effect permission.
2. Fresh packet-only recipient review for every one of the 12 R3 worker slices.
3. Accepted predecessor outputs before dependent slices dispatch.
4. PRD-03 target snapshot/application memory measurement and target SysFile/path/currentness qualification.
5. Exact `legacy_mapping_id` and mapping-sensitive raw-byte evidence for every claimed legacy runtime row.
6. A real current downstream CoUnit project for `VER-COU-023` unchanged-source compatibility compile.
7. `OPEN-COU-002`: exact runtime/support matrix and final release-owner decision after PRD-04 evidence.

## Author-time validation

The R3 packet validator checks the four required PRD structures and 21-row matrices, 12 slices, exact source archive identity/safety, 44 assertion methods, exact 60 public surfaces, R3 path-byte/mapping obligations, runtime-matrix shape and vocabulary, and xUnit positive/negative controls. It also runs the analytical UTF-8 path-boundary fixture. The final result is `PASS` for those author-time checks. This does not prove native CODESYS behavior or worker suitability.

**Implementation-ready: no.**  
**Approval:** all PRDs `CANDIDATE`; architecture `APPROVED`.  
**Dispatch:** all 12 slices `NOT_READY`.  
**Implementation acceptance:** not established.  
**Release/runtime support:** not established.
