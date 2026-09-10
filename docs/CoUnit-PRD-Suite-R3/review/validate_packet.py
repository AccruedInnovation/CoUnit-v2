#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json, re, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
notes: list[str] = []

expected_headings = [
    "Status and decision summary", "Repository discovery and current state", "Outcome, scope, and non-goals",
    "Interfaces and data contracts", "Canonical production and verification closure", "Bootstrap, staging, and migration",
    "State, effects, transactions, and recovery", "Source, install, runtime, and platform closure",
    "Integration, invalidation, and requalification", "Test and evidence plan", "Leaf implementation slices",
    "Risks, security, operations, and documentation", "Implementability matrix",
]
matrix_labels = [
    'Repository or new-project evidence, baseline, and current-state discovery',
    'Architecture binding, allocated scope, delegated design, and approval gates',
    'Target maturity, operating limits, and permitted claims',
    'Source precedence, design authority, and decision closure',
    'Outcome, scope, non-goals, and ownership',
    'Target worker, context fit, and bounded local choices',
    'Interfaces and field-level data contracts',
    'Canonical producer/recomputation/verifier closure',
    'Cross-artifact admission and consistency where required',
    'Non-circular bootstrap, staging, and migration',
    'State/effect/transaction/recovery semantics',
    'Source/build/install/runtime/platform closure',
    'Observed capabilities and filesystem boundaries',
    'Integration invalidation and requalification',
    'Author-set acceptance rules and schema-valid adversarial cases',
    'Supplied artifacts, reference availability, and author-time validation',
    'Leaf slices, file ownership, sequencing, and dispatch gates',
    'Worker-facing handoffs and fresh-context recipient review',
    'Set-equal allocated/local obligation coverage and cross-PRD acceptance ownership',
    'Open facts, decisions, assumptions, and late-bound values',
    'Security, operations, rollout, and documentation',
]

# Main PRDs and exact v4 shape.
for i in range(1, 5):
    p = ROOT / f"PRD-COU-0{i}" / "PRD.md"
    text = p.read_text(encoding='utf-8')
    heads = re.findall(r'^##\s+(\d+)\.\s+(.+?)\s*$', text, re.M)
    if [int(h[0]) for h in heads] != list(range(1, 14)) or [h[1] for h in heads] != expected_headings:
        errors.append(f"{p.relative_to(ROOT)}: 13-heading order mismatch")
    if 'Implementation-ready: no' not in text and '**Implementation-ready:** **no**' not in text:
        errors.append(f"{p.relative_to(ROOT)}: missing implementation-ready no verdict")
    if 'PARTIAL' not in text:
        errors.append(f"{p.relative_to(ROOT)}: expected PARTIAL status absent")
    msec = text.split('## 13. Implementability matrix', 1)[1] if '## 13. Implementability matrix' in text else ''
    present = [label for label in matrix_labels if f'| {label} |' in msec]
    if present != matrix_labels:
        errors.append(f"{p.relative_to(ROOT)}: implementability matrix missing/reordered rows: {[x for x in matrix_labels if x not in present]}")

# All 12 leaf packets exist and remain gated.
slices = sorted(ROOT.glob('PRD-COU-0?/slices/*.md'))
if len(slices) != 12:
    errors.append(f"expected 12 slices, found {len(slices)}")
for p in slices:
    if 'NOT_READY' not in p.read_text(encoding='utf-8'):
        errors.append(f"{p.relative_to(ROOT)}: missing NOT_READY dispatch/status")

# Relative markdown links resolve.
link_re = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
for p in ROOT.rglob('*.md'):
    text = p.read_text(encoding='utf-8', errors='replace')
    for target in link_re.findall(text):
        if target.startswith(('http://', 'https://', 'mailto:', '#')):
            continue
        target = target.split('#', 1)[0]
        if target and not (p.parent / target).resolve().exists():
            errors.append(f"{p.relative_to(ROOT)}: broken link {target}")

# No authoring template holes.
for p in ROOT.rglob('*.md'):
    text = p.read_text(encoding='utf-8', errors='replace')
    for bad in ('[path or URL', '[user-visible or operational outcome]', '[allowed scope:', '[Architecture package/archive/path'):
        if bad.lower() in text.lower():
            errors.append(f"{p.relative_to(ROOT)}: unresolved prompt placeholder {bad}")

# Exact source archive identity and traversal safety.
source_zip = ROOT / 'architecture/sources/CoUnitPlaintextExport.zip'
sha = hashlib.sha256(source_zip.read_bytes()).hexdigest()
expected_sha = '458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48'
if sha != expected_sha:
    errors.append(f'SRC-001 digest mismatch: {sha}')
with zipfile.ZipFile(source_zip) as z:
    names = z.namelist()
    unsafe = [n for n in names if Path(n).is_absolute() or '..' in Path(n).parts]
    if unsafe:
        errors.append(f'SRC-001 unsafe archive names: {unsafe[:3]}')
    zname_set = set(names)
    prefix = 'Unit Test Framework for CODESYS/'
    notes.append(f'SRC-001 entries: {len(names)}')

    # Assertion map.
    with (ROOT/'PRD-COU-02/contracts/assertion-family-map.csv').open(newline='', encoding='utf-8') as f:
        assertion_rows = list(csv.DictReader(f))
    if len(assertion_rows) != 44:
        errors.append(f"assertion-family-map expected 44 rows, got {len(assertion_rows)}")

    # R3-preserved public compatibility surface: exact symbol/kind set and source bindings.
    with (ROOT/'PRD-COU-04/qualification/public-api-surface.csv').open(newline='', encoding='utf-8') as f:
        api_rows = list(csv.DictReader(f))
    required = {(s, 'global_function') for s in ['RUN','RUN_IN_SEQUENCE','TEST','TEST_ORDERED','TEST_FINISHED','TEST_FINISHED_NAMED','IS_TEST_FINISHED']}
    required |= {(r['method'], 'FB_TestSuite_method') for r in assertion_rows}
    required |= {
        ('FB_TestSuite','function_block'),
        ('I_TestResults','interface'),
        ('I_TestResults.GetAreTestResultsAvailable','interface_method'),
        ('I_TestResults.GetTestSuiteResults','interface_method'),
        ('ST_TestCaseResult','type'), ('ST_TestSuiteResult','type'), ('ST_TestSuiteResults','type'),
        ('E_AssertionType','type'), ('GVL_Param_coUnit','global_constants'),
    }
    actual = {(r['symbol'], r['kind']) for r in api_rows}
    if len(api_rows) != 60:
        errors.append(f"public-api-surface expected 60 rows, got {len(api_rows)}")
    if actual != required:
        errors.append(f"public-api-surface set mismatch missing={sorted(required-actual)} extra={sorted(actual-required)}")
    for r in api_rows:
        zp = prefix + r['source_path']
        if zp not in zname_set:
            errors.append(f"public-api-surface missing source path in SRC-001: {r['source_path']}")
            continue
        b = z.read(zp)
        got_hash = hashlib.sha256(b).hexdigest()
        got_norm = ' '.join(b.decode('utf-8-sig').split())
        if r['sha256'] != got_hash:
            errors.append(f"public-api-surface hash mismatch: {r['symbol']}")
        if r['normalized_declaration'] != got_norm:
            errors.append(f"public-api-surface normalized declaration mismatch: {r['symbol']}")

# Runtime matrix schema and support-claim rules.
matrix_path = ROOT/'PRD-COU-04/qualification/runtime-matrix.csv'
with matrix_path.open(newline='', encoding='utf-8') as f:
    raw_matrix = list(csv.reader(f))
if not raw_matrix:
    errors.append('runtime matrix empty')
    matrix_fields = []
    matrix = []
else:
    matrix_fields = raw_matrix[0]
    for lineno, row in enumerate(raw_matrix[1:], start=2):
        if len(row) != len(matrix_fields):
            errors.append(f'runtime matrix line {lineno} has {len(row)} fields; expected {len(matrix_fields)}')
    with matrix_path.open(newline='', encoding='utf-8') as f:
        matrix = list(csv.DictReader(f))
required_fields = [
    'row_id','candidate_revision','candidate_hash','codesys_dev_system_version','compiler_version','runtime_controller','os_arch',
    'sysfile_version','cmpiectask_version','string_encoding_mode','legacy_mapping_id','snapshot_size_bytes','application_static_memory_bytes','project_or_fixture',
    'compile_status','run_all_status','run_sequence_status','assertion_status','xunit_status','restart_currentness_status','memory_budget_status',
    'public_compat_status','all_required_ver_status','integrated_scenarios_status','support_disposition','evidence_path','notes'
]
if matrix_fields != required_fields:
    errors.append('runtime matrix field contract mismatch')
if not matrix:
    errors.append('runtime matrix has no template row')
if len({r['row_id'] for r in matrix}) != len(matrix):
    errors.append('runtime matrix duplicate row_id')
statuses = {'PASS','FAIL','INCONCLUSIVE','NOT_RUN'}
status_fields = ['compile_status','run_all_status','run_sequence_status','assertion_status','xunit_status','restart_currentness_status','memory_budget_status','public_compat_status','all_required_ver_status','integrated_scenarios_status']
for r in matrix:
    for k in status_fields:
        if r.get(k) not in statuses:
            errors.append(f"runtime matrix {r.get('row_id')} bad {k}={r.get(k)!r}")
    if r.get('support_disposition') not in {'SUPPORTED','UNSUPPORTED','UNQUALIFIED'}:
        errors.append(f"runtime matrix {r.get('row_id')} bad support_disposition")
    mode = r.get('string_encoding_mode')
    mapping = r.get('legacy_mapping_id')
    if mode not in {'UTF8','LEGACY_SINGLE_BYTE','UNBOUND'}:
        errors.append(f"runtime matrix {r.get('row_id')} bad string_encoding_mode")
    if mode == 'UTF8' and mapping != 'N/A':
        errors.append(f"runtime matrix {r.get('row_id')} UTF8 row requires legacy_mapping_id=N/A")
    if mode == 'LEGACY_SINGLE_BYTE' and mapping in {'', 'UNBOUND', 'N/A', None}:
        errors.append(f"runtime matrix {r.get('row_id')} legacy row requires exact legacy_mapping_id")
    if mode == 'UNBOUND' and mapping not in {'UNBOUND', '', None}:
        errors.append(f"runtime matrix {r.get('row_id')} unbound encoding must not claim a mapping")
    if r.get('support_disposition') == 'SUPPORTED':
        if any(r[k] != 'PASS' for k in status_fields):
            errors.append(f"runtime matrix {r['row_id']} SUPPORTED without all PASS statuses")
        if mode == 'UNBOUND':
            errors.append(f"runtime matrix {r['row_id']} SUPPORTED with unbound encoding")
        if mode == 'UTF8' and mapping != 'N/A':
            errors.append(f"runtime matrix {r['row_id']} SUPPORTED UTF8 row with invalid legacy mapping")
        if mode == 'LEGACY_SINGLE_BYTE' and mapping in {'', 'UNBOUND', 'N/A', None}:
            errors.append(f"runtime matrix {r['row_id']} SUPPORTED legacy row without exact mapping")
        for k in ('snapshot_size_bytes','application_static_memory_bytes'):
            try:
                if int(r.get(k,'')) <= 0: raise ValueError
            except ValueError:
                errors.append(f"runtime matrix {r['row_id']} SUPPORTED without positive {k}")

# Independent host XML oracle controls.
py = sys.executable
script = ROOT/'PRD-COU-04/tools/verify_xunit.py'
def run_xml(name, expected=None):
    cmd=[py,str(script),str(ROOT/f'PRD-COU-04/fixtures/xunit/{name}')]
    if expected: cmd.append(str(ROOT/f'PRD-COU-04/fixtures/xunit/{expected}'))
    return subprocess.run(cmd,capture_output=True,text=True)
pos=run_xml('mixed-results.xml','mixed-results.expected.json')
if pos.returncode != 0:
    errors.append('xunit positive control failed: '+pos.stderr.strip())
negative_expect = {
    'bad-count.xml':'count mismatch',
    'bad-terminal.xml':'multiple terminal result children',
    'bad-assertions.xml':'assertions',
}
for name, needle in negative_expect.items():
    res=run_xml(name)
    if res.returncode == 0:
        errors.append(f'xunit negative control unexpectedly passed: {name}')
    elif needle.lower() not in res.stderr.lower():
        errors.append(f'xunit negative control failed for unexpected reason {name}: {res.stderr.strip()}')

# Key successor semantic guards stay present.
checks = {
    'PRD-COU-01/contracts/execution-core-contract.md': ['registration-time terminal case','AdvanceOrderedCursorPastTerminalRecords()','foreign task may set only'],
    'PRD-COU-02/contracts/assertion-engine-contract.md': ['255 data bytes','before any floating-point comparison or arithmetic','16#7F800000','signaling-NaN'],
    'PRD-COU-03/contracts/reporting-contract.md': ['do **not** emit a separate `status` attribute','`STRING` project-wide','Snapshot resource gate','PathByteLength(finalPath) <= 244','123 repetitions encode to 246 bytes'],
    'PRD-COU-04/contracts/qualification-contract.md': ['all seven public lifecycle/test façade functions','complete applicable `VER-COU-001..032`','bad-terminal.xml','legacy_mapping_id'],
}
for rel, needles in checks.items():
    text=(ROOT/rel).read_text(encoding='utf-8')
    for needle in needles:
        if needle not in text:
            errors.append(f'{rel}: missing successor guard {needle!r}')

# Local obligation coverage markers.
for rel, rids in {
    'PRD-COU-03/PRD.md':['L-COU03-006','R13-snapshot-memory','L-COU03-007','R14-path-byte-capacity'],
    'PRD-COU-04/PRD.md':['REQ-COU-032','L-COU04-001','L-COU04-002','L-COU04-003','L-COU04-004','L-COU04-005'],
}.items():
    text=(ROOT/rel).read_text(encoding='utf-8')
    for rid in rids:
        if rid not in text: errors.append(f'{rel} missing coverage marker {rid}')

# Active successor docs must not retain known superseded claims. Historical original-R1 evidence is excluded.
active_files=[p for prd_dir in sorted(ROOT.glob('PRD-COU-*')) for p in prd_dir.rglob('*.md')] + [ROOT/'README.md']
for p in active_files:
    text=p.read_text(encoding='utf-8',errors='replace')
    if 'Windows-1252 -> Unicode -> UTF-8' in text:
        errors.append(f'{p.relative_to(ROOT)} retains superseded hard-coded Windows-1252 conversion')
    if 'LEN(finalPath) <= 244' in text or 'LEN(P)<=244' in text:
        errors.append(f'{p.relative_to(ROOT)} retains superseded character-count path-capacity rule')

# Author-time analytical control for the UTF-8 path counterexample used by R14.
path_ok = 'é' * 122
path_bad = 'é' * 123
if not (len(path_ok) == 122 and len(path_ok.encode('utf-8')) == 244 and len((path_ok + '.counit.tmp').encode('utf-8')) == 255):
    errors.append('R14 UTF-8 accepted-boundary analytical fixture mismatch')
if not (len(path_bad) == 123 and len(path_bad.encode('utf-8')) == 246 and len((path_bad + '.counit.tmp').encode('utf-8')) == 257):
    errors.append('R14 UTF-8 rejected-boundary analytical fixture mismatch')
notes.append('R14 path-byte controls: UTF8 122×U+00E9=244 bytes accepted-boundary; 123×U+00E9=246 bytes rejected-boundary')
notes.append(f'runtime matrix row widths: {len(matrix_fields)} fields')

print('PASS' if not errors else 'FAIL')
print(f'PRDs: 4; slices: {len(slices)}; assertion methods: {len(assertion_rows)}; compatibility surface rows: {len(api_rows)}')
print(f'SRC-001 sha256: {sha}')
for note in notes: print(note)
print(f'xUnit controls: positive={pos.returncode}; negatives={len(negative_expect)} rejected')
if errors:
    for e in errors: print('ERROR:', e)
    raise SystemExit(1)
