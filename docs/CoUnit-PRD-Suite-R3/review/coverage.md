# PRD review coverage — R2 subject, R3 successor

**Original subject:** `COUNIT-PRD-SUITE-R2`, SHA-256 `67d3f8f61027b1970e8c4a3b592327c0f1e19488a76eca3476c1be08482a19e9`.  
**Successor:** `COUNIT-PRD-SUITE-R3`.  
**Architecture:** unchanged `COUNIT-ARCH-R3` / `2026-09-09-r3`, `APPROVED`.  
**Source baseline:** `SRC-001`, SHA-256 `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`.  
**Governing PRD contract:** v4 harmonized authoring/review workflow.

## Context accounting

The parent packet has four PRDs and 12 worker slices. Review was divided by PRD responsibility, material boundary, integrated scenario, supplied artifact, and worker handoff. The 665-entry source archive remained retrieve-for-check evidence rather than a mandatory simultaneous worker read. Each slice keeps a short read-now route to its parent §1, local contract, exact predecessor interface, fixtures/evidence needed for that task, and selected source rows.

No target worker capacity, active repository, compiler/target access, or actual predecessor implementation was supplied. Those are dispatch/qualification gates. This review therefore does not turn word counts into a capacity claim. The parent PRD set itself remained manageable through bounded units; no architecture-level PRD reallocation was needed.

## Bounded review units

| Unit | Main obligations / question | Result on R3 | Evidence / limit |
|---|---|---|---|
| execution local | `REQ-001..006,009..014,031,033,035`; runner/task/test lifecycle | no new R2 defect; historical `RF-001` repair preserved | PRD-01 + execution contract + S1/S2/S3; native compile/runtime future |
| assertion local | `REQ-001,004,007..008,015..021,034,037`; all 44 methods | no new R2 defect; historical `RF-002/007` repairs preserved | PRD-02 contract/map/slices; native FP/ANY/array tests future |
| reporting local | `REQ-001,022..031,036`; snapshot/log/XML/path/currentness | `RF-008` found and repaired | PRD-03 R3 contract/S2/S3; target SysFile/path runtime future |
| qualification local | `REQ-032` + final qualification contribution | `RF-009/010` found and repaired | PRD-04 contract/matrix/schema/S2/S3 + validator; native qualification future |
| public caller boundary | every R3-preserved public source surface | exact 60-entry source inventory still bound to `SRC-001` | host source/hash check passes; real downstream compile future |
| runner ↔ lifecycle | terminal/order/query behavior | R2 ordered-disabled cursor repair still closes the analytical counterexample | native case future |
| runner/lifecycle ↔ assertions | current-test segment/count reset/terminal effects | contracts agree | implementation future |
| assertions ↔ reporting | first failure/count/text limits | contracts agree; byte-bound diagnostic rules preserved | implementation future |
| snapshot ↔ publishers | one immutable truth and truthful result counts/states | contracts agree; xUnit oracle regression controls pass | actual PLC report future |
| CODESYS STRING ↔ report path | fixed byte capacity versus companion suffix derivation | `RF-008` repaired with stored-byte admission and distinct bounded append | analytical 122/123×U+00E9 control passes; native helper future |
| CODESYS STRING ↔ XML | project mode and exact legacy mapping versus support evidence | `RF-009` repaired with `legacy_mapping_id` + mapping-sensitive independent oracle | target mapping/raw-byte evidence future |
| report ↔ filesystem | path admission, stage/backup/currentness, I/O recovery | no effect allowed before safe path identities; staged commit semantics preserved | target fault injection future |
| evidence ↔ support | exact candidate/environment proof and non-averaging release claim | R2 rule preserved; R3 adds mapping requirement and valid CSV structure | validator passes; target rows future |
| integrated normal/order | `SCN-001..003,005` | joined semantics consistent | analytical review; runtime future |
| integrated failure/restart | `SCN-004,006..008` | task misuse/capacity/abort/restart/report currentness paths remain assigned; R3 path no-effect case added | analytical review; target runtime/fault evidence future |
| artifact validation | supplied CSV/schema/verifier/fixtures/source bindings | `RF-010` repaired; regression checks pass | author-time only; not product proof |
| recipient | all 12 leaf packets | same-context reconstruction refreshed for R3 | **not fresh**; v4 gate remains unsatisfied |

## Finding coverage

Historical findings retained as `FIXED_AND_RECHECKED`: `RF-001..RF-007`. New R2 findings:

- `RF-008` (`MAJOR`) — character-count report-path admission could exceed byte-sized `STRING(255)` capacity after reserved suffix append; R3 adds byte-count admission/bounded append/no-effect cases.
- `RF-009` (`MAJOR`) — legacy XML qualification could pass without proving the exact single-byte mapping; R3 adds `legacy_mapping_id` and mapping-sensitive independent raw-byte evidence.
- `RF-010` (`MODERATE`) — runtime-matrix template row had extra CSV cells and the R2 validator did not reject them; R3 repairs the CSV and validates exact row width.

All three new findings are `FIXED_AND_RECHECKED` at author/artifact level. No shared architecture amendment was needed.

## Allocation and set-equality review

The successor keeps R3 upstream allocations and adds only two source-supported local obligations:

- `O01 = U01 ∪ {L-COU01-001..003}`.
- `O02 = U02 ∪ {L-COU02-001..004}`.
- `O03 = U03 ∪ {L-COU03-001..007}`; `L-COU03-007` covers byte-safe companion-path admission.
- `O04 = {REQ-COU-032, L-COU04-001..005}` plus PRD-04's assigned final-verification contribution over `REQ-COU-001..037`; `L-COU04-005` covers exact legacy-mapping qualification.

Each member has a contract/state rule, slice, acceptance case/evidence destination, and owner. For design mapping, `M = O`; `O − M = ∅`; `M − O = ∅`. This is design traceability, not runtime acceptance.

PRD-04 remains the final integrated qualification owner. The CoUnit release/architecture owner remains final acceptance/support authority. No child slice drops a parent recovery, integration, or acceptance duty.

## Coverage limits

- No active implementation repository/candidate/local diff was supplied.
- No native CODESYS compile/runtime or target fault injection ran.
- No compiled snapshot/application memory measurement exists yet.
- No target legacy mapping identity/raw-byte result exists yet.
- No real downstream compatibility project was supplied.
- No actual PLC-generated xUnit report was parsed.
- No fresh recipient reviewed the R3 worker packets.
- No target-worker implementation trial ran or was authorized.
- No implementation acceptance or runtime/release support is established.
