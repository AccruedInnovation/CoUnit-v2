These methods are injected only into the disposable same-source qualification project.

- `ReadQualificationGuard` belongs to `FB_TestSuite`.
- `ReadQualificationBudget` and `RejectQualificationSuite` belong to `FB_coUnitRunner`.

The assertion/test overflow fixtures expose valid before/after state fields and require
`GuardPass`. They compare declaration identity, bounded counts, ordered cursor, first
failure presence, and assertion bookkeeping. The permitted OPEN-to-ERROR transition
is excluded from equality. No out-of-bounds address is read.

The suite overflow fixture initializes exactly 32 instances, then attempts a 33rd
registration before its first RUN using an existing valid suite pointer. Registration
does not deduplicate pointers; the capacity guard must reject this call. The test-only
method compares the committed count, last pointer, projection, active context, and
sequence cursor immediately around the rejected operation. This preserves production
declarations and avoids relying on initialization ordering for an external observer.

For `names`, complete healthy Device Log capture must contain each entry specified
by `expected.json.required_log_occurrences` exactly once. The native record oracle
also verifies that the conflicting normal-to-ordered declaration leaves the original
passed, unordered record and assertion count intact.
