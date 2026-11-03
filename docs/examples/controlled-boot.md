# Catalog selection and report checking

CoUnit's public `RUN_CONTROLLED` exchange is owned and called cyclically by the
application. [The catalog example](catalog.md) describes command ordering,
identity, selection and acknowledgment. A consumer must supply its own authorized
build and runtime workflow; installing the library does not provide one.

`tools/controlled_boot.py` contains historical literal-catalog parsing utilities
and a host adapter for 2.1.0.1–2.1.0.5. Its host-specific build/run path is not a
supported current workflow. `tools/accept_run.py` checks completed controlled
reports separately; see [report checking](host-acceptance.md).
