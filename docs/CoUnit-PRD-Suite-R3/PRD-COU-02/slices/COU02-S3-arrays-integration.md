# COU02-S3 — Array assertion families and assertion-engine integration

**Dispatch:** `NOT_READY` — requires accepted `COU02-S1/S2` and bound repository.  
**Obligations:** `REQ-COU-001`, `016`, `018..019`, plus complete PRD-02 evidence contribution.

## Read now

- `../contracts/assertion-engine-contract.md` §6 and common §§1–4.
- `../contracts/assertion-family-map.csv` array rows.
- exact accepted S1/S2 candidate/evidence.
- source export array assertion methods.

## Outcome and steps

1. Preserve all 1-D, 2-D, and 3-D public array signatures.
2. Compare extents by dimension; allow different lower bounds with equal extents and compare by offset.
3. Use typed element equality; REAL/LREAL arrays use the exact scalar float rule.
4. Stop at first mismatch for diagnostics; never retain/copy whole arrays as assertion history.
5. Route each array call through one common assertion outcome transaction and correct array `E_AssertionType`.
6. Run the full 44-method assertion-family map and provide candidate/evidence for PRD-03/04.

Exit requires no wrong `E_AssertionType`, no double-count through helper dispatch, correct max-per-invocation count, and bounded memory under repeated scans.
