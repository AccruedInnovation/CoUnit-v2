# CoUnit 2.1.0.6 source

This tree is the canonical inspectable 2.1.0.6 source for the accompanying `counit_2.1.0.6.library`. Object hierarchy and child methods/properties are preserved. The packaged library also retains native project information, compiler settings and library references.

Use `tools/import_candidate.py` with explicit source, target, tools and report paths to update an isolated library copy. Never direct a whole-tree export into another project's source directory. Read-back compares declarations and implementations; final validation must also install the saved library and compile a consumer, because source equality alone does not detect stale native language models.
