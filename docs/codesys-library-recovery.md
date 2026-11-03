# Recovering CODESYS library state

A downstream consumer of the unchanged CoUnit 2.0.0.0 package produced cascading parser errors concentrated in a few methods: truncated VAR_INPUT/type names, duplicated declarations and malformed newline fragments. Authoritative plaintext and ScriptEngine read-back were well formed. Reloading/reinstalling the original package and regenerating the language model with Clean All restored successful builds and tests. This is evidence of installation/language-model state involvement, not proof of a particular internal CODESYS defect.

## Recovery sequence

1. Preserve the original diagnostics, resolved library version, compiler version and authoritative source. Distinguish malformed installed-source tokens from ordinary test or product errors.
2. Work in the authorized disposable project/runtime. Unload the affected reference, clean the project and reload the unchanged package for the affected exact version; if needed, reinstall it through Library Repository and rebind the reference. For 2.1.0.7 use [counit_2.1.0.7.library](../counit_2.1.0.7.library) or its matching compiled library, and confirm native version 2.1.0.7 and namespace CoUnit. The 2.0.0.0 recovery evidence above remains specific to that version. Clean All regenerates language models and requires a subsequent download before login.
3. Capture a fresh complete build. If errors persist, compare declarations, bodies, parent/interface relationships and nested methods against canonical plaintext. Do not infer 85 independent logic bugs from cascading malformed-token diagnostics.
4. Run a fresh installed-library consumer test with the [v2 acceptance checks](counit-v2-testing.md#native-execution-and-acceptance), then verify reopening/rebuilding where installation recovery is being qualified.

Do not silently downgrade to 1.x or publish a speculative source-repair package. Preserve earlier failures even after a clean reload passes. Successful source imports alone do not prove that a saved/installed library resolves correctly in a consumer.

## ScriptEngine and imports

Use the existing bulk PLCOpenXML route for source/shard replacement: generate one complete document, clear the intended importable scope, import once and reacquire object handles. Per-object creation/replacement loops are unsuitable for bulk library imports.

Handle Clean All, reload and export dialogs through ScriptEngine prompt handling, restoring the previous prompt settings afterward. Use a fresh explicit export destination, or explicitly handle overwrite confirmation. An unattended overwrite dialog has caused an MCP timeout while the IDE script remained active; transport timeout is not proof of cancellation. Resolve the dialog or script state before more mutations.

The split DEC/IMP export is this project's own plaintext representation, not CODESYS File-Based Storage or PLCopenXML. It does not contain every native project setting or reference. See [the distribution README](../README.md); preserve native configuration when rebuilding the packaged library.
