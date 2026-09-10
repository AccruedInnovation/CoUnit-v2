# Runtime qualification matrix contract

`runtime-matrix.csv` is the canonical qualification-row projection for `VER-COU-025`. Each executed row binds one exact accepted CoUnit candidate to one exact CODESYS compiler/runtime environment and one named native project/fixture.

Required rules:

- Replace every `UNBOUND` field needed for the row before execution. Do not execute a row with an unbound candidate, toolchain, runtime, platform, required library version, project, or project-wide `STRING` encoding mode.
- `string_encoding_mode` is exactly `UTF8`, `LEGACY_SINGLE_BYTE`, or `UNBOUND`. It records the project-wide CODESYS `UTF8 Encoding for STRING` setting/equivalent evidence for the row.
- `legacy_mapping_id` is `N/A` for `UTF8`, `UNBOUND` until a legacy mapping is established, or an exact stable mapping identifier for `LEGACY_SINGLE_BYTE`. The evidence path must retain the independent compiler/runtime basis for that identifier. A broad label such as `LEGACY_SINGLE_BYTE` is not itself the mapping ID.
- `snapshot_size_bytes` records the compiled `SIZEOF` of the R3 final snapshot type/equivalent. `application_static_memory_bytes` records the relevant bound application/static-memory figure used for the resource check. Use `UNBOUND` until measured; a `SUPPORTED` row requires positive integer values and `memory_budget_status=PASS`.
- Status fields use only `PASS`, `FAIL`, `INCONCLUSIVE`, or `NOT_RUN`.
- Focused status fields are `compile_status`, `run_all_status`, `run_sequence_status`, `assertion_status`, `xunit_status`, `restart_currentness_status`, and `memory_budget_status`.
- Joined qualification fields are `public_compat_status`, `all_required_ver_status`, and `integrated_scenarios_status`. `all_required_ver_status=PASS` means every applicable `VER-COU-001..032` is `PASS` on the same compatible evidence binding or is covered by an explicit checked unaffected-evidence rule. `integrated_scenarios_status=PASS` means `SCN-COU-001..008` have been joined and passed on compatible bindings; it is not inferred from local passes.
- `support_disposition` uses `SUPPORTED`, `UNSUPPORTED`, or `UNQUALIFIED`.
- `SUPPORTED` requires every focused and joined status above to be `PASS`, a bound encoding mode, a valid mapping identity for that mode (`N/A` only for UTF-8; exact non-`UNBOUND` mapping for legacy), measured positive snapshot/static-memory values, and no proof-relevant `UNBOUND` identity field.
- If any required status is `FAIL`, disposition is `UNSUPPORTED`. If none fails but any required status is `INCONCLUSIVE` or `NOT_RUN`, disposition is `UNQUALIFIED`.
- `candidate_hash` binds the actual library/project source used by that row, not the PRD archive.
- `evidence_path` names a retained compile/runtime evidence directory or report that contains the commands/actions, exact environment, result logs, memory/encoding evidence, any legacy mapping source plus mapping-sensitive raw-byte expected/observed results, and produced report artifacts.
- A failed or inconclusive row stays visible. Do not average it with passing rows or widen support from a different environment.
- Adding a new environment adds a row; it does not rewrite prior observations.
