# COU03-S3 — xUnit publication commit and restart recovery

**Dispatch:** `NOT_READY` — requires repository and accepted `COU03-S1/S2`; target SysFile behavior must be available for tests.  
**Obligations:** `REQ-COU-029..031`, `036`; closes implementation of detailed decision `DD-COU03-001`.

## Read now

- `../contracts/reporting-contract.md` §§7–12.
- `../../architecture/shared-contracts.md` `IF-COU-005`, `SDE-COU-003`, `ISC-COU-004`.
- `../../review/platform-api-evidence.md`.
- accepted S1/S2 candidate.

## Outcome and fixed work

Use reserved `P.counit.tmp` and `P.counit.bak` paths only after S2's byte-capacity admission has produced nontruncated, NUL-terminated, pairwise-distinct companion paths. Reconcile stale companions, write/close only staging, preserve current final at backup before commit, rename complete stage to final as the semantic commit, restore prior final on failed commit where possible, and never emit success before commit.

## Required fault cases

Before fault injection, assert the companion-path admission cases from `R14-path-byte-capacity`: accepted boundary paths yield exact distinct companions; rejected byte-overflow paths cause no `Probe`, `OpenWrite`, `Rename`, or `DeleteIfPresent`. Then inject or simulate failure at probe/delete/open/write/flush(real error)/close/final->backup rename/stage->final rename/restore. For every pre-commit failure, current final is prior complete or absent; partial bytes exist only under stage. After successful commit, backup cleanup failure is a warning and does not rewrite `WRITTEN`.

Stop if the target cannot provide a checked rename operation within the configured filesystem. Do not fall back to direct final-path writing without architecture-owner review proving the same currentness invariant.
