# COU03-S2 — UTF-8 XML escaper and bounded stream writer

**Dispatch:** `NOT_READY` — requires repository and accepted `COU03-S1`.  
**Obligations:** `REQ-COU-027..030` writer contribution; `QAS-COU-006/007`.

## Read now

- `../contracts/reporting-contract.md` §§4–6, 8.
- source export: `FB_xUnitXmlPublisher`, `FB_XmlControl`, `FB_FileControl`, config GVL.
- `../../architecture/shared-contracts.md` `IF-COU-005` XML semantics.

## Outcome and fixed work

1. Replace whole-document buffer use in xUnit publication with bounded byte chunk.
2. Emit deterministic root/suite/test counts and exactly one testcase result child.
3. Bind the project-wide CODESYS `STRING` encoding at preflight. In UTF-8 mode, validate/re-emit UTF-8 without legacy transcoding. In legacy mode, bind the exact byte-to-Unicode mapping identified by PRD-04 qualification evidence; do not infer it from the broad `LEGACY_SINGLE_BYTE` label. Replace malformed/forbidden XML code points with U+FFFD, then apply XML attribute escaping.
4. Implement the contract's byte-counted path helper and bounded companion append. Do not use character-count `LEN()` as the UTF-8 capacity proof; reject overflow/truncation/aliasing before file effect.
5. Check each SysFile write result and exact returned byte count.
6. Support documents larger than one configured chunk by flushing before capacity exhaustion.
7. Do not yet make stage output current; S3 owns semantic commit.

Exit evidence: parser-valid metachar fixture; non-ASCII UTF-8 fixture in a UTF-8 project; a legacy mapping fixture that includes raw bytes whose decoded result depends on the bound mapping; malformed UTF-8/replacement fixture where target input can produce it; 244-byte accepted and >244-byte rejected path cases including the UTF-8 122/123 × U+00E9 boundary; and a report larger than one chunk that parses completely with exact counts. Evidence records both the broad encoding mode and the exact legacy mapping identity when applicable.
