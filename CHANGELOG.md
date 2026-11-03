# Changelog

## 2.1.0.7

- Adds opt-in scan tracing. Native build, export, read-back and bounded
  installed-consumer runs passed. A complete timeout trace remains unverified.
  A real sink failure could not be induced; its error path remains untested and
  is an accepted limitation. See [scan tracing](docs/scan-tracing.md). Existing
  2.1.0.6 artifacts remain unchanged.

## 2.1.0.6 — qualification candidate

- Adds `CONFIGURE_LEGACY_RUN` to bind run, build and target identity for legacy
  runner execution. It does not create catalog case/row identity.
- Retains the 2.1 controlled catalog, guarded test entry, structured assertions,
  fixture and temporal helpers, and XML/optional JSON reporting.
- Native export/readback, installed-byte verification and bounded legacy-mode
  execution passed for the recorded environment. Additional bounded controlled
  catalog, selection, execution, cancellation and reset journeys have evidence;
  they do not qualify arbitrary workflows. See [qualification](docs/upgrade-plan.md).

## 2.1.0.5 — earlier candidate

- Introduced incremental catalog preparation, controlled execution, stable
  case/row identities, bounded fixture and temporal helpers, richer diagnostics
  and report identity. Exact capacity and runtime observations are version-specific.

## 2.0.1.0 — reporting candidate

- Added optional independent diagnostic JSON and bounded expected/actual failure
  details. XML and JSON have independent publication outcomes.

## 2.0.0.0 — public baseline

- Reworked execution, assertion and reporting behavior while retaining the normal
  CoUnit authoring model. The 1.2.0.3 compatibility source remains in
  `compatibility/1.2.0.3`.
