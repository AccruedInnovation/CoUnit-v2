# COU02-S2 — Scalar, floating-point, and generic ANY assertions

**Dispatch:** `NOT_READY` — requires bound repository and accepted `COU02-S1`.  
**Obligations:** `REQ-COU-001`, `015..021`, `034`; `VER-COU-009..013` scalar/ANY contribution.

## Read now

- `../contracts/assertion-engine-contract.md` §§5, 7, 9.
- `../contracts/assertion-family-map.csv` filtered to non-array methods.
- source export: public scalar/ANY assertion implementations, `F_AnyToUnionValue`, `F_IsAnyEqualToUnionValue`, `U_ExpectedOrActual`, `E_AssertionType`.

## Outcome and steps

1. Preserve every scalar/ANY public signature.
2. Route each public wrapper through `BeginAssertion` exactly once and private comparator logic.
3. Map each typed family to its exact `E_AssertionType`; generic ANY remains `Type_ANY`.
4. Implement guarded REAL/LREAL algorithm exactly: raw-bit IEEE classification occurs before any floating-point comparison/arithmetic, then apply NaN/infinity/negative-delta/finite tolerance rules.
5. Implement descriptor-first ANY checks; logical bounded STRING/WSTRING compare; exact-size primitive dispatch; bytewise fallback for unsupported same-type/equal-size values.
6. No arbitrary-size `MEMCPY` to a fixed union/string and no public-wrapper recursion.

Required negative tests must reach each guard: type mismatch, primitive size mismatch, null descriptor pointer if a safe harness can construct it, unterminated bounded string descriptor if constructible, negative/NaN delta, quiet-NaN operands, signaling-NaN operands where the target can preserve their bit patterns, infinity combinations, and differing user-defined byte representation. NaN fixtures must be created from raw IEEE bit patterns without first evaluating the NaN in floating-point logic.
