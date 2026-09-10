# CODESYS platform API evidence used by the PRD design

**Observation date:** 2026-09-09  
**Purpose:** support bounded PRD-level selections for cross-task fault latching and xUnit publication. This is supporting evidence, not a replacement for target qualification under `PRD-COU-04`.

## Atomic cross-task latch

CODESYS documents the `TEST_AND_SET` operator as accepting a writable `DWORD`, atomically writing `1`, returning the prior value, and remaining atomic on multicore platforms. PRD-COU-01 therefore uses one `DWORD` as a one-way *violation notification only*. A foreign task never writes CoUnit's complex run/test state. The bound task consumes the latch and performs the framework-error transition.

Source: <https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_operator_test_and_set.html>

## SysFile publication primitives

The current SysFile reference documents:

- `SysFileOpen`: returns `RTS_INVALID_HANDLE` on failure; `AM_WRITE` creates or overwrites a file.
- `SysFileWrite`: returns the number of bytes written and also accepts `pResult`; both are checked by the PRD.
- `SysFileFlush`: returns an explicit result and may report `ERR_NOTIMPLEMENTED` or `ERR_NOT_SUPPORTED`.
- `SysFileClose`: returns an explicit result.
- `SysFileRename`: renames old path to new path and returns a result.
- `SysFileDelete`: deletes a named file and returns a result.

Sources:

- <https://content.helpme-codesys.com/en/libs/SysFile/Current/SysFileOpen.html>
- <https://content.helpme-codesys.com/en/libs/SysFile/Current/SysFileWrite.html>
- <https://content.helpme-codesys.com/en/libs/SysFile/Current/SysFileFlush.html>
- <https://content.helpme-codesys.com/en/libs/SysFile/Current/SysFileClose.html>
- <https://content.helpme-codesys.com/en/libs/SysFile/Current/SysFileRename.html>
- <https://content.helpme-codesys.com/en/libs/SysFile/Current/SysFileDelete.html>

The docs do **not** establish that rename-over-existing is atomic or even supported on every target. PRD-COU-03 therefore does not depend on overwrite-by-rename. It uses explicit staging, backup, and restore states and leaves target support subject to `PRD-COU-04` qualification.

## STRING encoding and storage size

Current CODESYS documentation states that `STRING(n)` capacity is byte-based and that a UTF-8 character can occupy up to four bytes. The Standard-library `LEN` function, by contrast, returns the **number of characters**. Therefore a `LEN(P) <= 244` test cannot prove that an 11-byte suffix fits a `STRING(255)` path when project-wide UTF-8 is enabled. A concrete boundary is 123 repetitions of U+00E9: `LEN` is 123, but the stored UTF-8 content is 246 bytes and the `.counit.tmp` result would require 257 content bytes.

CODESYS documentation also distinguishes project-wide UTF-8 from its legacy single-byte setting; current datatype help describes the non-UTF-8 form as Latin-1, while other CODESYS help/version wording has used broader ASCII/legacy labels. The qualification design therefore records the broad mode and, for a claimed legacy profile, an exact evidence-backed mapping identity plus a mapping-sensitive raw-byte case rather than allowing the product converter to define its own oracle.

Sources:

- <https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_dlg_project_settings_compile_options.html>
- <https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_datatype_string.html>
- <https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_utf8_encoding.html>
- <https://content.helpme-codesys.com/en/libs/Standard/Current/String-Functions/LEN.html>

R3 binds the active encoding mode at repository/target preflight, uses stored-byte bounds for path/string capacity, and requires exact legacy mapping evidence when that mode is claimed.

## REAL/LREAL representation

CODESYS documents `REAL` as IEEE-754 32-bit and `LREAL` as IEEE-754 64-bit. The R2 assertion contract therefore classifies raw IEEE exponent/fraction/sign bits before floating-point comparison or arithmetic, so quiet or signaling NaN values do not need to be evaluated by `x <> x` before they are recognized.

Source:

- <https://content.helpme-codesys.com/en/CODESYS%20Development%20System/_cds_datatype_real.html>

This is a design-level portability guard. Exact target behavior remains native qualification evidence.
