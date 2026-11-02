# Agent directions for CoUnit v2

Read [README.md](README.md), [the v2 testing guide](docs/counit-v2-testing.md), [REPORTING.md](REPORTING.md) and [qualification/README.md](qualification/README.md) before changing tests or the harness.

- Consumer runners instantiate selected suites and call exactly one RUN mode from one task. CoUnit invokes suites; never duplicate suite calls or switch RUN/RUN_IN_SEQUENCE mid-run.
- Keep stateful fixtures and phases in suite-owned storage. TEST is not a control-flow guard, and sequential mode is not fixture isolation. Preserve explicit completion and cleanup.
- Distinguish ordinary consumer test success from framework qualification. Deliberate failures, empty inventories and documented internal fault-injection hooks are valid only when checked against their independent qualification oracles. Do not copy those hooks into shipping or consumer code.
- Use a fresh report path and exact selected inventory. V2 consumer success requires NORMAL disposition as well as passing cases. Preserve failing attempts and separate test truth, publication success and cleanup.
- `compatibility/1.2.0.3` is a historical baseline; do not modify it to match v2 or use old internals as current authoring guidance. Test Manager and TcUnit APIs are not interchangeable with CoUnit.
- PlaintextExport is the inspectable source. Update `generate_assertions.py` when changing generated assertions. Preserve the source/package distinction: a source-only change is not a validated installed-library release.
- Use the existing XML/native tools with explicit project/output paths. Import a complete shard once rather than looping through object creation. Resolve prompt/timeout state before further IDE mutations; see [library recovery](docs/codesys-library-recovery.md).
- Native runs require an explicitly selected authorized test runtime. Do not infer physical-controller permission from a simulator qualification task.

For documentation-only changes, check links and keep examples consistent with actual signatures; do not regenerate packages or qualification evidence unnecessarily. For code changes, use the development checks in README.md and the relevant native qualification shards. Do not expand supported runtime claims beyond the recorded matrix.
