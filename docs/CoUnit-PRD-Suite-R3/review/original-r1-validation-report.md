# CoUnit PRD Suite R1 — author-time validation report

**Subject:** `/CoUnit-PRD-Suite-R1` before final archive packaging.  
**Architecture:** `COUNIT-ARCH-R3` / `2026-09-09-r3`.  
**Result:** structural/mechanical author-time checks `PASS`; native implementation/runtime and fresh-recipient checks are not part of this pass.

## Checks actually run

`python review/validate_packet.py` returned `PASS` and checked:

- four `PRD.md` files exist;
- each PRD contains the required 13 main headings, exactly numbered and in the required order;
- each implementability matrix contains all 21 required row labels;
- all four PRDs state implementation-ready `no` and retain `PARTIAL` status;
- exactly 12 leaf slice packets exist and each carries `NOT_READY` dispatch/status text;
- all relative Markdown links resolve within the delivered directory;
- selected source-prompt placeholder forms are absent;
- `PRD-COU-02/contracts/assertion-family-map.csv` contains 44 assertion method rows;
- `PRD-COU-04/qualification/public-api-surface.csv` contains 50 unique `(kind,symbol)` records: six lifecycle/test façade functions plus 44 assertion methods;
- the runtime-matrix template has a row identity and no duplicate current row ID;
- `SRC-001` SHA-256 is exactly `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`;
- `SRC-001` archive names contain no absolute or `..` traversal paths;
- PRD-04 declares and traces `REQ-COU-032` and `L-COU04-001..004`;
- the supplied independent xUnit parser accepts `mixed-results.xml` with its expected JSON;
- the same parser rejects `bad-count.xml`, demonstrating that a plausible wrong count does not false-pass this oracle.

Raw structural output is retained in `validation-raw.txt`. Positive/negative xUnit outputs are retained under `../PRD-COU-04/evidence/`.

## Semantic self-review performed

The author reviewed:

- PRD-01 public façade ↔ runner, runner ↔ suite/test, and foreign-task ↔ owner boundaries;
- PRD-02 runner/test context ↔ assertion bookkeeping, public wrapper ↔ private comparator, and assertion outcome ↔ first-failure/count boundaries;
- PRD-03 terminal execution ↔ final snapshot, snapshot ↔ legacy/log/XML consumers, stream writer ↔ file adapter, and publisher ↔ external current-report semantics;
- PRD-04 public consumer ↔ public surface, product candidate ↔ regression corpus, report ↔ independent parser/currentness harness, and evidence ↔ support claim/release owner;
- integrated normal/sequence/branch, abort/error, restart, capacity/cross-task, and report-currentness scenarios against the same R3 semantics.

`author-only-consumption.md` records same-context reconstruction for all 12 worker packets. It did **not** count as fresh-recipient evidence.

## Context-size observations

`word-counts.txt` records rough word counts only. Main PRDs are about 3,900–5,200 words; individual worker packets are about 145–584 words, with local contracts about 867–1,911 words. These counts support the chosen staged reading routes, but they are not model-capacity measurements. The actual target worker/access profile must be checked before dispatch.

## Checks not run / claims not established

- no active implementation repository, branch/commit/local changes or writable code path was available;
- no repaired CoUnit implementation was compiled;
- no native CODESYS Development System/compiler/runtime/target qualification ran;
- no task or SysFile fault injection ran on a target;
- no actual PLC-generated xUnit report was parsed by the supplied host verifier;
- no real downstream current CoUnit project was available for `VER-COU-023`;
- no fresh packet-only recipient review was available;
- no target-worker implementation trial ran;
- no implementation acceptance, release approval, production-control claim, or general runtime-support claim was established.

These limits are reflected in each PRD's `PARTIAL` status and each slice's `NOT_READY` dispatch gate.

## Final archive check policy

The final ZIP is created only after substantive content freezes. A separate extraction is compared byte-for-byte with the reviewed directory as the final delivery check. That check is reported with the delivered archive rather than written back into this file afterward, so the check does not alter the bytes it claims to validate.
