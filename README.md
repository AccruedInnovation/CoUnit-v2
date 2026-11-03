# CoUnit 2.1.0.7

CoUnit is an xUnit-style unit-testing library for CODESYS. It provides test
suites, assertions, cyclic execution and xUnit reports, with optional JSON
diagnostics, catalog-based case selection and [scan tracing](docs/scan-tracing.md).

**Validation scope:** Native checks cover selected journeys on CODESYS 3.5.22.20
and Linux Virtual Control SL 4.22 x64. Online change, physical controller
deployment and native UTF-8 compiler configurations are not qualified. See
[qualification and limitations](docs/upgrade-plan.md) and the scan-tracing guide
for version-specific evidence and known limitations.

## Get started

1. Install [counit_2.1.0.7.compiled-library](counit_2.1.0.7.compiled-library)
   through the CODESYS Library Repository. In your test application's Library
   Manager, select version **2.1.0.7** under namespace `CoUnit`.
2. Follow the [first passing test](docs/2.1-upgrade.md#first-passing-test) to
   create a suite and cyclic runner in a disposable test application.
3. Capture the fresh xUnit report and verify its disposition, selected cases and
   results. The runner completion flag alone does not mean the tests passed.

The [source library](counit_2.1.0.7.library) is the editable native container;
[PlaintextExport](PlaintextExport/README.md) is its inspectable source, not a
replacement for native project settings and references. Keep existing jobs pinned
to their provider until they deliberately migrate, then rebuild and download a
fresh application. See [migration](docs/2.1-upgrade.md#allocation-and-migration).

## Documentation

- [User guide](docs/2.1-upgrade.md): installation, runner ownership, tests,
  reports, catalog selection, fixtures and migration.
- [Testing guide](docs/counit-v2-testing.md): multi-scan tests and practical
  acceptance checks.
- [Examples](docs/examples/diagnostic-arithmetic.md): structured assertion and
  progress reporting; [catalog](docs/examples/catalog.md) and
  [temporal helpers](docs/examples/cooperative-fixture-and-expectation.md).
- [Report acceptance](REPORTING.md), [changes](CHANGELOG.md), and
  [qualification and limitations](docs/upgrade-plan.md).
- [Library-state recovery](docs/codesys-library-recovery.md) and
  [agent directions](AGENTS.md).

## Essential rules

Instantiate selected suites in persistent program storage and call exactly one
runner cyclically from one task. CoUnit calls registered suites; do not call the
suite FB separately. Guard new test bodies with `TEST_GUARDED` or `BeginCase`,
and call `TEST_FINISHED` only after the final observation. Stateful fixtures and
phase storage must survive across invocations. Keep reports fresh and verify the
exact selected inventory; publication and test success are separate outcomes.

## Development checks

Python 3.13 and the standard library are used for the repository checks. Some
host integration tests additionally require the separately supplied historical
2.1.0.5 helper and fixtures; without them the full discovery command reports
missing-dependency errors. `COUNIT_BOOT_HELPER` points to that helper and
`COUNIT_ADAPTER_ROOT` selects a writable scratch directory. The helper is not
included in this repository and is not a supported execution route:

```powershell
python generate_assertions.py --check
python qualification/check_public_api.py
python -m unittest discover -s qualification -p 'test_*.py'
python qualification/check_runtime_matrix.py qualification/runtime-matrix.csv
```

These checks do not replace a native installed-library consumer build or runtime
qualification. See [qualification](qualification/README.md).

## License

CoUnit v2 is derived from CoUnit 1.2.0, distributed under the MIT License. See
[LICENSE](LICENSE) for attribution and license terms.
