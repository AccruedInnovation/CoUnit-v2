# CoUnit 2.0.0 source

The 599 declaration/implementation sections in this tree are the canonical inspectable source for the accompanying `counit_2.0.0.library` (native version 2.0.0.0). Object hierarchy and child methods/properties are preserved. The packaged library also retains native project information, compiler settings and library references.

Use `tools/import_candidate.py` with explicit source, target, tools and report paths to update an isolated library copy. Never direct a whole-tree export into another project's source directory. Read-back compares declarations and implementations; final validation must also install the saved library and compile a consumer, because source equality alone does not detect stale native language models.
