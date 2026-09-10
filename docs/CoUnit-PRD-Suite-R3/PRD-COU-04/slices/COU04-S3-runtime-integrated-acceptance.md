# COU04-S3 — Runtime matrix and integrated qualification assembly

**Parent:** `PRD-COU-04`  
**Status:** `NOT_READY`  
**Reason:** depends on accepted COU04-S1/S2 outputs, accepted PRD-01/02/03 candidate, actual target access, and fresh recipient review.

## Outcome and allocation

Execute `VER-COU-025` and assemble the final integrated disposition for `VER-COU-001..032`, `SCN-COU-001..008`, and the committed architecture obligations. Produce an evidence-bound support recommendation without granting release approval.

## Required reading — read now

1. `../PRD.md` §§1, 5, 8–13;
2. `../contracts/qualification-contract.md` entire file;
3. `../qualification/runtime-matrix-schema.md` and `runtime-matrix.csv`;
4. architecture `verification-and-readiness.md`;
5. accepted S1/S2 evidence indexes.

Retrieve producer PRD contracts only when a failure or change requires checking its exact semantic source.

## Entry gate

- exact implementation candidate frozen for qualification;
- COU04-S1/S2 accepted and their evidence paths accessible;
- actual CODESYS compiler/runtime environment(s) and target permission available;
- no unresolved mixed-revision evidence;
- fresh packet-only recipient review passes for this slice.

## Settled design and steps

1. Create one runtime-matrix row per exact environment and fill every required binding before execution, including project `STRING` encoding mode, `legacy_mapping_id` (`N/A` for UTF-8; exact evidence-backed mapping for legacy), and compiled snapshot/application memory figures.
2. Build/import the candidate in a clean native environment using the project's accepted build/install route. Record all required library/component versions.
3. Execute the qualification suites and host/report checks. Populate status cells only from retained evidence.
4. For each `VER-COU-001..032`, select evidence with a compatible candidate/contract binding. If evidence comes from an earlier unchanged area, record the unchanged dependency argument; otherwise re-run.
5. Reconstruct each `SCN-COU-001..008` from compatible observations and verify shared assumptions. Do not join results from different semantic candidates unless the scenario's unaffected portions are proven equivalent.
6. Check totals, task ownership, assertion count/failure truth, xUnit currentness, restart behavior, and support claims together for the integrated candidate.
7. Populate `public_compat_status`, `all_required_ver_status`, and `integrated_scenarios_status` only from joined evidence. Mark a runtime row `SUPPORTED` only if **every** focused and joined status, including memory budget, is `PASS`; encoding/mapping/memory identity is bound; any legacy row has mapping-sensitive S2 evidence; and no required proof field is `UNBOUND`. Otherwise use `UNSUPPORTED` for a required fail or `UNQUALIFIED` for missing/inconclusive evidence.
8. Produce final evidence report with failures preserved and a release recommendation. Do not write `APPROVED`; final acceptance owner is the CoUnit release/architecture owner.

## Currentness and invalidation

Any semantic code change after qualification invalidates the affected evidence set under `CON-COU04-001 §8`. A different compiler/runtime row needs its own evidence. A documentation-only change may reuse product evidence if candidate source identity and contracts remain unchanged.

## Exit gate

- all applicable `VER-COU-001..032` have `PASS` or a visible blocking disposition;
- all eight integrated scenarios have compatible evidence and explicit outcomes;
- public compile cohort result is included;
- runtime matrix has no fabricated or inferred versions, encoding modes, legacy mapping IDs, or memory measurements;
- recommendation scope exactly matches passing rows;
- release owner can accept or reject without reconstructing missing test semantics.
