# CoUnit PRD Suite R2 adversarial review and R3 repair

## 1. Review status and subject

**Mode:** `REVIEW_AND_REVISE` under the supplied v4 adversarial-review contract.  
**Governing authoring edition:** `05-PRD-implementability-authoring-prompt-v4.md`, harmonized v4, 2026-09-08.  
**Unchanged candidate:** `COUNIT-PRD-SUITE-R2`, supplied as `CoUnit-PRD-Suite-R2(1).zip`, SHA-256 `67d3f8f61027b1970e8c4a3b592327c0f1e19488a76eca3476c1be08482a19e9`.  
**Original PRD revisions:** `PRD-COU-01-R2`, `PRD-COU-02-R2`, `PRD-COU-03-R2`, `PRD-COU-04-R2`, all dated 2026-09-09.  
**Successor packet:** `COUNIT-PRD-SUITE-R3`, dated 2026-09-09. PRD-01/02 remain R2 because this review found no supported need to change their controlling text; PRD-03/04 advance to R3.  
**Architecture:** unchanged embedded `COUNIT-ARCH-R3` / `2026-09-09-r3`, `APPROVED`.  
**Source baseline:** embedded CoUnit 1.2.0.3 plaintext export `SRC-001`, SHA-256 `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`, 665 archive entries.  
**Review authority used:** source-supported consistency, detailed acceptance, reference, artifact, and worker-handoff repair only. No shared R3 contract, requirement allocation, public compatibility promise, risk acceptance, support promise, or release decision changed.

The R2 packet's top-level status was already conservative and remains correct after repair: each PRD is `PARTIAL` and `CANDIDATE`, every one of the 12 slices is `NOT_READY`, and `Implementation-ready: no`. The R2 packet also correctly said implementation acceptance and runtime/release support were not established. This review does not convert any of those claims to a pass.

The unchanged R2 candidate was reviewed before repair. Coverage included all four main PRDs, all four local contract surfaces, all 12 leaf worker packets, the supplied qualification data and verifier, material PRD boundaries, the embedded R3 assignment and verification records, and the source snapshot where current-source claims mattered. Review was split into local, boundary, integrated, artifact, and worker-consumption units rather than treating a successful package validator as semantic proof.

The current session was already exposed to prior project and authoring context before this review and later authored the R3 repairs. It therefore cannot serve as the mandatory fresh-context recipient. No independent agent/session/human recipient was available through the supplied environment. The same-context recipient reconstruction was refreshed and is labeled author-only. The v4 fresh-recipient check remains `NOT_RUN`, so the relevant matrix row remains `PARTIAL` and no PRD can become overall `PASS` from this review.

No implementation trial was authorized or run. No product repository was modified. No CODESYS native compile/runtime, target filesystem fault injection, real downstream consumer compile, or release qualification was performed.

**Final review assessment:** three new supported defects were found in R2: two `MAJOR` and one `MODERATE`. All three were repaired in R3 and rechecked at the author/artifact level. Seven historical R1 findings already fixed by R2 were retained and checked for regression. No new shared-architecture change is required.

**Stop reason:** all supported repairs available under current authority are applied and affected author-time checks pass. The remaining gates require external/current inputs or independent evidence: active repository/toolchain/worker binding, accepted predecessor implementations, target runtime evidence, a real downstream consumer for compatibility, the release runtime matrix, and a genuinely fresh packet-only recipient review.

## 2. Intent, preserved design, and strongest risks

The packet must let a smaller CODESYS implementation worker repair CoUnit without inventing public behavior or test semantics. The authorized outcome remains the R3 design: deterministic runner/lifecycle behavior, bounded assertion handling, one immutable final result snapshot, truthful log/xUnit projections, staged report publication, and evidence-bound compatibility/runtime qualification.

The review preserved these R2 decisions because they remain sound and consistent with R3:

- one owner task mutates complex run/test state; cross-task misuse uses the small atomic violation signal rather than shared complex mutation;
- disabled/terminal tests do not block ordered progression;
- one assertion transaction occurs per public assertion call, with bounded failure text and atomic first-failure capture;
- floating-point special values are classified from raw representation before ordinary comparison behavior is applied;
- the result snapshot is the one source for legacy results, logging, and xUnit output;
- xUnit is streamed through a bounded writer and becomes current only after the staged publication protocol completes;
- public compatibility is checked against the exact preserved surface and ultimately by a real downstream consumer compile;
- runtime support remains an exact environment claim with non-averaging evidence; local passes cannot conceal failed or missing integrated proof;
- snapshot size remains fixed by the architecture and must be qualified on each target rather than silently reduced by an implementation worker.

The new R2 risks were not about missing headings. They allowed a worker or acceptance path to satisfy the written packet while still producing a wrong result:

1. PRD-03 used character count to enforce a byte-sized `STRING(255)` report-path limit. A UTF-8 path could pass admission but leave too few bytes for the reserved publication suffix.
2. PRD-03 required the exact legacy single-byte mapping, but PRD-04's qualification row and acceptance case did not require that mapping identity or a mapping-sensitive independent oracle. A wrong legacy decoder could therefore pass.
3. The canonical runtime-matrix CSV had a wider data row than header because a notes field contained unquoted commas. The supplied validator accepted that malformed row, so its `PASS` overclaimed what it checked.

These three defects are local to path admission and qualification evidence. Their smallest repair does not change the reserved `.counit.tmp` / `.counit.bak` protocol, the xUnit text policy, the supported encoding modes, any public CoUnit surface, or the R3 architecture.

## 3. Evidence-backed findings

### RF-008 — report companion-path admission used character count for a byte-capacity contract

- **Severity / confidence:** `MAJOR` / high.
- **Subject:** unchanged R2 `PRD-COU-03/contracts/reporting-contract.md` §6, mirrored in PRD-03 §4 and the report/publication worker path.
- **Kind / governing basis:** detailed-design and acceptance defect. The v4 authoring contract requires field/path bounds, exact error behavior, and acceptance cases that settle consequential behavior rather than leave it to the worker. R3/R2 reporting semantics also require failed publication to leave no partial current report and require the stage/backup topology to be safe before effects.
- **Expected:** for `T_MaxString=STRING(255)`, the final path must leave enough stored-byte capacity for either reserved 11-byte ASCII suffix; overflow, truncation, or aliasing must be rejected before filesystem effects.
- **Actual R2 rule:** the contract required `LEN(finalPath) <= 244`. In CODESYS UTF-8 mode, the string capacity is byte-based while `LEN` counts characters. The rule therefore does not prove that 11 suffix bytes fit.
- **Reproducible analytical counterexample:** suffix length is 11 bytes. A path of 122 U+00E9 characters uses 244 UTF-8 bytes; adding a suffix yields 255 bytes and fits the declared content capacity. A path of 123 U+00E9 characters uses 246 UTF-8 bytes; adding a suffix needs 257 bytes and cannot fit. The R2 character-count admission still accepts it because 123 is below 244. Evidence is retained in `review/r2-probe-evidence.txt` and `review/platform-api-evidence.md`.
- **Strongest rebuttal:** an implementation worker could choose a safer append helper even though the contract names `LEN`. That does not close the finding. The contract makes the character-count precondition normative and the worker is explicitly not allowed to redesign observable/error behavior. Two otherwise reasonable workers could therefore disagree on whether the second path is admissible.
- **Consequence / reach:** a compliant R2 implementation could truncate or overflow a companion path, or fail to prove that final/stage/backup identities remain distinct before `Probe/Open/Rename/Delete`. This weakens `REQ-COU-030/036`, the publication-currentness design, and PRD-04's fault tests.
- **Smallest repair / authority:** source-supported local refinement. R3 defines `PathByteLength`, requires a bounded append, exact NUL termination, exact `P_bytes + 11` length, pairwise byte-distinct identities, and rejection before any file effect. It adds `L-COU03-007` and `R14-path-byte-capacity`, including 244/245-byte ASCII and 122/123 × U+00E9 UTF-8 boundaries. No shared path names or publication state machine changed.
- **Affected set:** PRD-03 §§1,4,7,9,10,12; reporting contract; COU03-S2/S3; PRD-04 acceptance and COU04-S2; packet validator.
- **Closure:** `FIXED_AND_RECHECKED`. The successor validator executes the analytical byte-boundary control and checks the new normative markers. Native CODESYS path-helper/file behavior remains future implementation evidence and is not claimed passed.

### RF-009 — legacy XML qualification did not bind or distinguish the exact single-byte mapping

- **Severity / confidence:** `MAJOR` / high.
- **Subject:** unchanged R2 PRD-04 runtime matrix/schema, `contracts/qualification-contract.md`, and COU04-S2 legacy XML acceptance path, in relation to PRD-03 reporting contract §5.
- **Kind / governing basis:** acceptance/evidence defect. The v4 authoring contract requires a semantic guard's fixture and expected result to reach and prove that guard independently. R2 PRD-03 already requires legacy mode to bind the exact target single-byte mapping rather than guess it.
- **Expected:** a support claim for `LEGACY_SINGLE_BYTE` must identify the exact byte-to-Unicode mapping used on that compiler/runtime/project and must prove converter behavior with raw bytes whose expected logical text comes from evidence independent of the converter under test.
- **Actual R2 qualification:** the runtime matrix recorded only `string_encoding_mode=LEGACY_SINGLE_BYTE`; there was no exact mapping field. COU04-S2 required a legacy non-ASCII fixture, but did not require a byte that distinguishes plausible mappings or require the expected Unicode result to come from external mapping evidence.
- **Analytical counterexample:** a defective converter can use the wrong meaning for byte `0x80` while still correctly handling a less discriminating byte such as `0xE9`. If the chosen legacy fixture exercises only the latter, the broad `LEGACY_SINGLE_BYTE` row and XML case can pass while the converter remains wrong for the actual project mapping.
- **Strongest rebuttal:** the row's generic `evidence_path` could contain the exact mapping even without a dedicated field, and a worker might select a strong legacy fixture. That is possible but not required. The row acceptance rule could still be marked supported without a checkable mapping identity, and the fixture could legally be non-distinguishing under R2. The packet therefore allowed two different acceptance standards.
- **Consequence / reach:** PRD-04 could qualify XML text semantics for a legacy environment despite a wrong byte decoder. This affects `REQ-COU-027`, `REQ-COU-032`, `VER-COU-019/025`, and the runtime support claim.
- **Smallest repair / authority:** restore the already-required PRD-03 mapping rule into the qualification contract. R3 adds `legacy_mapping_id`: `N/A` for UTF-8, `UNBOUND` until legacy evidence exists, and an exact evidence-backed value for legacy rows. `SUPPORTED` cannot be claimed with an unbound mapping. COU04-S2 now requires mapping-sensitive raw-byte cases (including `0x80` and `0xE9` where representable) and an expected result derived from retained compiler/runtime mapping evidence, not from the PLC converter. This adds local `L-COU04-005` and `DD-COU04-006`; it does not pick a mapping in advance or expand platform support.
- **Affected set:** PRD-03 S2 context; PRD-04 §§1,4,5,8,10–12; qualification contract; runtime matrix/schema; COU04-S2/S3; validator.
- **Closure:** `FIXED_AND_RECHECKED` at design/artifact level. The CSV and validator enforce the mode/mapping coupling. Actual mapping identity and raw-byte target result remain future row evidence, as they should.

### RF-010 — runtime-matrix CSV row width was malformed and the validator did not notice

- **Severity / confidence:** `MODERATE` / high.
- **Subject:** unchanged R2 `PRD-COU-04/qualification/runtime-matrix.csv` and `review/validate_packet.py`.
- **Kind / governing basis:** supplied-artifact and author-time validation defect. The v4 authoring contract requires actual supplied artifacts to be mechanically checked and requires reported validation to match what the check can prove.
- **Expected:** each runtime-matrix data row must have exactly the same field count as its declared CSV header; the author-time validator must reject extra cells.
- **Actual:** the R2 header had 26 fields and the template data row had 29. The free-text notes cell contained three unquoted commas. Python `csv.DictReader` stored the extra values under its overflow key, but the R2 validator checked named fields only, so it still returned `PASS`.
- **Strongest rebuttal:** a human could infer that the trailing cells belong to notes, and some consumers might ignore extras. That is not enough for a canonical machine-readable matrix whose packet claims author-time validation. A generic CSV reader does not recover the intended 26-field record without special handling.
- **Consequence / reach:** tooling can read a different record shape than the schema claims, and the packet's validation report can say `PASS` while the canonical CSV is malformed. This is bounded but can create avoidable evidence-tool failures or hidden field loss during qualification.
- **Smallest repair / authority:** R3 rewrites the row with normal CSV quoting and, as part of RF-009, adds the explicit mapping column. The final header and row both have 27 fields. The validator now parses raw rows first and rejects any width mismatch before `DictReader` semantic checks.
- **Affected set:** runtime matrix/schema, qualification contract, validator, validation report.
- **Closure:** `FIXED_AND_RECHECKED`; final validator reports `runtime matrix row widths: 27 fields`.

### Historical findings retained from the R1 → R2 review

These are not new R2 defects. They remain in the register so the successor does not lose review history. The current R3 checks did not find a regression in their repaired surfaces.

| ID | Prior severity | Prior cause | Current disposition |
|---|---|---|---|
| `RF-001` | MAJOR | disabled ordered registration could leave the canonical cursor stuck | `FIXED_AND_RECHECKED` — R2/R3 execution contract and S2 retain immediate canonical cursor advancement |
| `RF-002` | MAJOR | hard-coded legacy text handling and character-based fixed-string sizing | `FIXED_AND_RECHECKED` — mode-bound XML handling and byte-bounded diagnostic behavior retained; RF-008/009 refine two remaining edges |
| `RF-003` | MAJOR | preserved public compatibility surface was incomplete | `FIXED_AND_RECHECKED` — exact 60-row source surface remains checked against `SRC-001` |
| `RF-004` | MODERATE | xUnit oracle/fixture was weaker than required semantics | `FIXED_AND_RECHECKED` — positive fixture plus three negative controls retained and validator exercises them |
| `RF-005` | MAJOR | support projection could overclaim from grouped local passes | `FIXED_AND_RECHECKED` — all-VER/all-scenario non-averaging row rule retained |
| `RF-006` | MAJOR | fixed result snapshot had no target memory feasibility gate | `FIXED_AND_RECHECKED` — compiled snapshot/application memory qualification remains a target gate |
| `RF-007` | MAJOR | ordinary FP expression could touch NaN before raw special-value classification | `FIXED_AND_RECHECKED` — raw IEEE classification remains normative in PRD-02 |

No `CRITICAL` finding is supported. The review considered, but did not promote, other possible complaints: the snapshot is large but R2 already has the correct target feasibility gate; xUnit parser reuse does not by itself defeat oracle independence; the PRD-01/02 worker freedom left is private implementation detail rather than observable design; and missing future native code/results are not PRD-stage defects when their acceptance semantics and producers are fully specified.

## 4. Design, artifact, and coverage audit

### 4.1 Thirteen-section audit

| PRD section | R3 review result | Main evidence / remaining limit |
|---|---|---|
| 1. Status and decision summary | adequate after repair | status/approval/dispatch/acceptance remain separate; R3 adds only local repair decisions; external gates remain explicit |
| 2. Repository discovery and current state | deliberately partial | exact embedded source evidence exists; active implementation repo/toolchain/local changes still absent |
| 3. Outcome, scope, and non-goals | preserved | R3 allocation and final acceptance ownership unchanged; new local obligations trace to existing outcome |
| 4. Interfaces and data contracts | repaired | PRD-03 path admission now byte-accurate; PRD-04 runtime row carries exact legacy mapping identity |
| 5. Canonical production and verification closure | repaired where affected | report currentness remains one staged protocol; support rows cannot trust a broad legacy-mode label |
| 6. Bootstrap, staging, and migration | adequate | future predecessor availability is explicit and non-circular; no missing current tool is relabeled as a slice output |
| 7. State, effects, transactions, and recovery | repaired where affected | companion paths must be valid/distinct before filesystem effects; existing commit/recovery protocol unchanged |
| 8. Source, install, runtime, and platform closure | partial by design evidence | platform docs support the design; actual repo/target versions and native behavior remain future bindings |
| 9. Integration, invalidation, and requalification | adequate | RF-008 affects PRD-03/04 path tests; RF-009 affects PRD-03 text contract ↔ PRD-04 support row; both counterpart checks refreshed |
| 10. Test and evidence plan | repaired | path byte boundary and mapping-sensitive legacy cases now have independent expected properties; future product checks remain `NOT_RUN` |
| 11. Leaf implementation slices | repaired where affected | all 12 remain coherent; COU03-S2/S3 and COU04-S2/S3 now carry the new admission/mapping rules; all remain `NOT_READY` |
| 12. Risks, security, operations, and documentation | repaired where affected | wrong path capacity and wrong legacy mapping now have trigger/detection/response/evidence gates |
| 13. Implementability matrix | consistent | all four PRDs remain `PARTIAL`; no repair was used to inflate readiness |

### 4.2 Final 21-dimension status audit

The table below records the status in each final PRD, not an averaged suite score.

| Dimension | PRD-01 | PRD-02 | PRD-03 | PRD-04 | Review note |
|---|---|---|---|---|---|
| Repository or new-project evidence, baseline, and current-state discovery | PARTIAL | PARTIAL | PARTIAL | PARTIAL | active repo/candidate/toolchain not supplied |
| Architecture binding, allocated scope, delegated design, and approval gates | PASS | PASS | PASS | PASS | embedded R3 assignment/revisions preserved |
| Target maturity, operating limits, and permitted claims | PASS | PASS | PASS | PASS | no release/runtime overclaim |
| Source precedence, design authority, and decision closure | PASS | PASS | PASS | PASS | new repairs derive from existing local rules; no reserved shared choice taken |
| Outcome, scope, non-goals, and ownership | PASS | PASS | PASS | PASS | unchanged allocation/owners |
| Target worker, context fit, and bounded local choices | PARTIAL | PARTIAL | PARTIAL | PARTIAL | actual worker/access/capacity still dispatch-bound |
| Interfaces and field-level data contracts | PASS | PASS | PASS | PASS | RF-008/009 repaired affected contracts |
| Canonical producer/recomputation/verifier closure | PASS | PASS | PASS | PASS | no alternate report/support authority added |
| Cross-artifact admission and consistency where required | PASS | PASS | PASS | PASS | PRD-03 now proves companion-path admission before effects |
| Non-circular bootstrap, staging, and migration | PASS | PASS | PASS | PASS | future predecessors have explicit producers/gates |
| State/effect/transaction/recovery semantics | PASS | PASS | PASS | PASS | staged publication and recovery preserved; path rejection now precedes effects |
| Source/build/install/runtime/platform closure | PARTIAL | PARTIAL | PARTIAL | PARTIAL | exact active build/install/target route still missing |
| Observed capabilities and filesystem boundaries | PASS | PASS | PARTIAL | PARTIAL | reporting/qualification depend on future target observations |
| Integration invalidation and requalification | PASS | PASS | PASS | PASS | affected PRD-03↔04 evidence routes refreshed |
| Author-set acceptance rules and schema-valid adversarial cases | PASS | PASS | PASS | PASS | R14 and mapping-sensitive cases added; xUnit controls retained |
| Supplied artifacts, reference availability, and author-time validation | PASS | PASS | PASS | PASS | R3 artifact checks pass; future predecessor/target outputs remain correctly classified |
| Leaf slices, file ownership, sequencing, and dispatch gates | PARTIAL | PARTIAL | PARTIAL | PASS | PRD-04 design slices are complete but `NOT_READY`; 01–03 also lack repo/predecessor mapping |
| Worker-facing handoffs and fresh-context recipient review | PARTIAL | PARTIAL | PARTIAL | PARTIAL | every-slice fresh review remains `NOT_RUN` |
| Set-equal allocated/local obligation coverage and cross-PRD acceptance ownership | PASS | PASS | PASS | PASS | no dropped allocation; PRD-04 remains final integration owner |
| Open facts, decisions, assumptions, and late-bound values | PASS | PASS | PASS | PASS | remaining items are explicit evidence/dispatch bindings, not hidden semantic design choices |
| Security, operations, rollout, and documentation | PASS | PASS | PASS | PASS | scoped test-library operating exposure; execution permission remains external |

No row is `BLOCKED` in the final candidate. The overall status of each PRD remains `PARTIAL` because at least one required row is `PARTIAL`. This is non-averaging.

### 4.3 Allocation and set-equality

The successor preserves the upstream `U` sets from R3 and the existing justified local obligations. This review adds only two local obligations that express already-required local behavior:

- `O01 = U01 ∪ {L-COU01-001, L-COU01-002, L-COU01-003}`.
- `O02 = U02 ∪ {L-COU02-001, L-COU02-002, L-COU02-003, L-COU02-004}`.
- `O03 = U03 ∪ {L-COU03-001..007}`; R3 adds `L-COU03-007` for byte-safe companion-path admission.
- `O04 = {REQ-COU-032, L-COU04-001..005}` plus PRD-04's assigned final-verification contribution over `REQ-COU-001..037`; R3 adds `L-COU04-005` for exact legacy mapping evidence.

Semantic trace review connects each member of these local obligation sets to a controlling rule, slice, acceptance case/evidence destination, and acceptance owner. At the **design mapping** level, `M = O`; `O − M = ∅`; `M − O = ∅`. This does not claim the future implementation satisfies `O`, and it does not accept the whole architecture from component evidence.

PRD-01/02/03 keep product-behavior ownership. PRD-04 remains the final integrated qualification owner. The CoUnit release/architecture owner remains the final acceptance/support authority.

### 4.4 Bounded local, boundary, and integrated review units

| Unit | Main question | R3 result / evidence limit |
|---|---|---|
| PRD-01 execution local | runner/suite/test/order/task lifecycle complete and still consistent after R2 | no new defect; historical RF-001 remains closed; native compile/runtime future |
| PRD-02 assertion local | all 44 public assertion methods share settled count/outcome/FP/ANY/array rules | no new defect; historical RF-002/007 remain closed; native FP behavior future |
| PRD-03 reporting local | snapshot/log/XML/path/publication rules fully decide worker behavior | RF-008 found and repaired; target SysFile behavior future |
| PRD-04 qualification local | artifacts/oracles/runtime support rules can detect intended failures | RF-009/010 found and repaired; native qualification future |
| public caller boundary | preserved API surface remains exact | 60-entry source inventory validator passes; real downstream compile remains future `VER-COU-023` |
| runner ↔ lifecycle | terminal skip/order/query behavior joined | no regression from R2 ordered-skip repair |
| assertions ↔ reporting | first failure/count/text bounds have same meaning on both sides | consistent; byte bounds retained |
| snapshot ↔ xUnit | one final truth, bounded encoding, independent semantic oracle | consistent after R3 mapping/path refinements |
| CODESYS STRING ↔ report path | declared string capacity and publication companion derivation agree | RF-008 repaired with stored-byte admission |
| CODESYS STRING ↔ XML qualification | producer decoding rule and verifier support row identify same legacy mapping | RF-009 repaired; target mapping evidence future |
| report ↔ filesystem | no path effect before safe companion identities; staged commit remains currentness boundary | design closed; target fault tests future |
| evidence ↔ support | exact row binding cannot average away missing/failed evidence | R2 rule retained; R3 adds mapping identity; CSV shape fixed |
| integrated normal/order | R3 normal, sequence, lifecycle paths keep compatible premises | analytical review consistent; runtime future |
| integrated failure/restart | task misuse, capacity, abort/restart, report-currentness, file failure paths retain explicit owner/gate | analytical review consistent; target fault/runtime evidence future |
| recipient | all 12 worker packets usable without hidden semantic choices | same-context author-only reconstruction complete; **fresh requirement unsatisfied** |

### 4.5 Artifact/reference audit

The packet supplies or exactly references the local contracts, 12 slice entry points, source snapshot, 44-method assertion map, 60-row public compatibility map, defect/verification map, xUnit positive and negative fixtures, host xUnit verifier, runtime-matrix schema/template, platform evidence, validator, and review records. No future implementation output is mislabeled as already supplied.

The final runtime matrix has 27 columns and every delivered row has exactly 27 cells. `legacy_mapping_id` has explicit coupling to `string_encoding_mode`. The xUnit positive fixture is accepted and three targeted negative controls are rejected. The source archive identity and traversal check pass. No self-hashing or recursive metadata system was introduced.

## 5. Recipient and worker evidence

`review/author-only-consumption.md` records a packet-only-style reconstruction of every leaf slice after the R3 repairs. It states each slice's outcome/contribution, first substantive actions, inputs and predecessor classes, normal/error/recovery behavior, acceptance/evidence path, local freedom, escalation route, context route, invalidation conditions, and conditional dispatch status.

The review found no remaining instruction that asks the worker to choose public behavior, define an error precedence, invent a support rule, or author its own acceptance standard. The R3 repair specifically changes the affected worker view as follows:

- `COU03-S2` must implement stored-byte path admission/bounded append and bind the project text mode; it may not use a character count as the capacity proof.
- `COU03-S3` may begin file operations only after companion identities satisfy the admission rule; rejected path cases must show no filesystem effect.
- `COU04-S2` must bind the exact legacy mapping and exercise mapping-sensitive raw bytes against an independent expected value, and it must run the path byte-boundary/no-effect cases before filesystem fault work.
- `COU04-S3` may mark a legacy runtime row supported only when the exact mapping ID and mapping-sensitive evidence are present in addition to all other non-averaging gates.

The author-only review is **not** fresh evidence. This session saw prior authoring/project context before packet consumption and later wrote the repairs. No context reset or role change can make it fresh. No independent recipient was available, and no target-worker trial was authorized. Therefore:

- fresh recipient observation: `NOT_RUN` for all 12 slices;
- target-worker empirical suitability: not established;
- dispatch status: all 12 slices remain `NOT_READY` under their current gates;
- implementation acceptance: not established.

Later slices may be fully designed while waiting for predecessors; the packet correctly distinguishes that from dispatch readiness.

## 6. Repairs and successor validation

### 6.1 R3 changes

**PRD-03 canonical changes**

- revision advanced to `PRD-COU-03-R3`;
- added `DD-COU03-006` and `L-COU03-007`;
- replaced the character-count companion-path admission with `PathByteLength(finalPath) <= 244` by stored content bytes;
- specified bounded suffix append, NUL termination, exact `+11` content-byte length, and pairwise byte-distinct final/stage/backup paths;
- specified rejection before any file probe/open/rename/delete on overflow, truncation, missing terminator, or alias;
- added ASCII 244/245 and UTF-8 122/123 × U+00E9 acceptance boundaries and no-effect checks;
- refreshed COU03-S2/S3 worker instructions, integration invalidation, risk, and evidence rows.

**PRD-04 canonical changes**

- revision advanced to `PRD-COU-04-R3`;
- added `DD-COU04-006` and `L-COU04-005`;
- added `legacy_mapping_id` to the canonical runtime-matrix contract and CSV;
- requires `N/A` in UTF-8 mode and exact evidence-backed identity in legacy mode; a legacy `UNBOUND` mapping cannot support the row;
- added mapping-sensitive legacy raw-byte acceptance with an independent expected mapping;
- added PRD-03 path byte-boundary/no-effect acceptance to the report compatibility slice;
- repaired the CSV data row and strengthened the validator to enforce exact row width and mode/mapping coupling.

**Review/support changes**

- `review/r2-probe-evidence.txt` preserves the unchanged-candidate counterexamples and malformed-CSV observation;
- `review/platform-api-evidence.md` records the byte-capacity versus character-count distinction and keeps exact legacy mapping as target evidence rather than guessing it;
- `review/author-only-consumption.md`, `review/coverage.md`, this report, README, validation report/raw output, and context counts are refreshed for R3.

No architecture file, source snapshot, product implementation file, public compatibility declaration, xUnit terminal-state model, or release policy was changed.

### 6.2 Affected-set derivation

RF-008 changes a PRD-03 publication admission rule, so its affected set includes the reporting contract, PRD-03 state/effect and test sections, COU03-S2/S3, PRD-04 report-compatibility acceptance, and worker-consumption evidence. It does not alter PRD-01/02 behavior or public source compatibility.

RF-009 changes qualification evidence needed to prove an existing PRD-03 decoder rule, so its affected set includes PRD-03 S2 context, PRD-04 runtime-row contract/schema, XML acceptance, S2/S3, support decision, and recipient evidence. It does not select or change the target legacy mapping.

RF-010 changes the canonical qualification CSV and its validator, so it requires artifact parsing/schema/validation rechecks but no product-semantic requalification.

The existing xUnit negative controls, 44 assertion map, 60 public surface map, source identity, and unrelated PRD-01/02 design evidence remain valid because their proof inputs did not change. The validator reruns them as regression controls.

### 6.3 Checks actually run

The unchanged R2 validator was run first against the original extracted subject and returned `PASS`. That observation is retained because it demonstrates the limit that led to RF-010: the old check could pass the malformed CSV and did not test RF-008/009.

R3 author-time checks then included:

- safe archive/path inspection of the supplied package and embedded source archive;
- analytical UTF-8 path boundary: 122 × U+00E9 = 244 bytes and suffix fits exactly; 123 × U+00E9 = 246 bytes and must be rejected before file effects;
- raw CSV width check: R2 header/data widths `26/29`; R3 widths `27/27`;
- strengthened packet validator across all four PRDs, 12 slices, source bindings, assertion/public-surface inventories, mapping/path guards, runtime matrix, and xUnit controls;
- Python syntax compilation of the packet validator and host xUnit verifier;
- final archive construction and extraction/path-integrity checks at delivery.

The final validation output is retained in `review/validation-raw.txt` and summarized in `review/validation-report.md`.

Checks **not** run: native CODESYS build/runtime tests, real worker implementation, two-task stress tests, target SysFile faults, target rename/flush semantics, compiled snapshot memory measurement, exact target legacy mapping observation, actual PLC-generated report parsing, real downstream consumer compile, full runtime-matrix qualification, fresh recipient review, and release acceptance.

### 6.4 Finding dispositions

| Finding | R3 disposition | Recheck state |
|---|---|---|
| RF-008 | `FIXED_AND_RECHECKED` | analytical byte boundary + contract/slice/validator checks pass; native target behavior remains future evidence |
| RF-009 | `FIXED_AND_RECHECKED` | mapping field/coupling and mapping-sensitive acceptance rule present and validator-enforced; target mapping result remains future evidence |
| RF-010 | `FIXED_AND_RECHECKED` | final CSV width exactly matches header and validator rejects width mismatch |
| RF-001..007 | `FIXED_AND_RECHECKED` historical | affected R2 controls retained; successor validator regression checks pass |

## 7. Open decisions, evidence gaps, and handoff

There is no new user decision required to accept these R3 document repairs. The remaining items are external evidence/access gates or later acceptance authority, not unresolved local design choices.

1. **`OPEN-COU-001` — active implementation binding.** Owner: implementation/integration owner. Bind the writable repository/project, exact candidate and local changes, CODESYS toolchain/runtime/target, worker access, and allowed effects before dispatch. A contradiction with fixed R3 assumptions returns to the proper owner.
2. **Fresh packet-only recipient review.** Owner: PRD review/integration owner. A genuinely fresh recipient must consume every slice using only its worker packet and declared access. Record actual retrievals, answers, guesses/interventions, and per-slice disposition. Until then, the worker-handoff row stays `PARTIAL` and all current slices remain `NOT_READY`.
3. **Accepted predecessors.** Owners: PRD-01/02/03 implementation and integration owners. Later slices wait for the exact predecessor outputs named in their entry gates; design completeness does not make those outputs available.
4. **PRD-03 target feasibility.** Owner: PRD-03 implementation plus PRD-04 qualification. Measure compiled snapshot and application static memory; qualify target file API/result/rename/flush behavior; run report path/fault/restart cases. If a support target cannot satisfy the fixed representation/protocol, route the needed architecture change rather than weakening the worker packet.
5. **Exact legacy mapping evidence.** Owner: PRD-04 qualification for each legacy row. Bind the compiler/runtime/project mapping ID from independent evidence and run mapping-sensitive raw-byte XML cases. A row with `UNBOUND` mapping stays unqualified.
6. **Real downstream compatibility project.** Owner: PRD-04. `VER-COU-023` requires at least one current real CoUnit consumer project compiled unchanged against the accepted candidate; the source-surface inventory is only a preflight.
7. **`OPEN-COU-002` — runtime/support closure.** Owner: CoUnit release/architecture owner after PRD-04 evidence. Only exact rows satisfying every required non-averaging gate, including mapping and memory evidence, may become supported. This review grants no release approval.

**Successor entry point:** `README.md`.  
**Worker entry points:** each `PRD-COU-0N/PRD.md` §1 then its named slice and exact local contract.  
**Review evidence:** `review/prd-review.md`, `review/coverage.md`, `review/validation-report.md`, `review/author-only-consumption.md`, `review/r2-probe-evidence.txt`.  
**Final design status:** all four PRDs `PARTIAL`, approval `CANDIDATE`, `Implementation-ready: no`.  
**Dispatch:** all 12 slices `NOT_READY`.  
**Implementation acceptance / runtime support:** not established.
