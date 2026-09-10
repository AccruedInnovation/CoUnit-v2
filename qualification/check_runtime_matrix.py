"""Enforce R3 runtime support dispositions and exact proof bindings."""
import csv
import sys
from pathlib import Path

STATUSES = ('compile_status', 'run_all_status', 'run_sequence_status', 'assertion_status',
            'xunit_status', 'restart_currentness_status', 'memory_budget_status',
            'public_compat_status', 'all_required_ver_status', 'integrated_scenarios_status')
IDENTITIES = ('row_id', 'candidate_revision', 'candidate_hash', 'codesys_dev_system_version',
              'compiler_version', 'runtime_controller', 'os_arch', 'sysfile_version',
              'cmpiectask_version', 'project_or_fixture', 'evidence_path')


def check(rows):
    errors, seen = [], set()
    if not rows:
        return ['runtime matrix has no rows']
    for row in rows:
        name = row.get('row_id', '')
        if not name or name in seen:
            errors.append(f'{name}: missing or duplicate row ID')
        seen.add(name)
        values = [row.get(key) for key in STATUSES]
        if any(value not in {'PASS', 'FAIL', 'INCONCLUSIVE', 'NOT_RUN'} for value in values):
            errors.append(f'{name}: invalid status')
        expected = 'UNSUPPORTED' if 'FAIL' in values else 'SUPPORTED' if all(v == 'PASS' for v in values) else 'UNQUALIFIED'
        if row.get('support_disposition') != expected:
            errors.append(f'{name}: status values require {expected}')
        if expected != 'SUPPORTED':
            continue
        for key in IDENTITIES:
            if row.get(key, '').strip() in {'', 'UNBOUND', 'N/A'}:
                errors.append(f'{name}: unbound {key}')
        mode, mapping = row.get('string_encoding_mode'), row.get('legacy_mapping_id')
        if mode not in {'UTF8', 'LEGACY_SINGLE_BYTE'} or (mode == 'UTF8' and mapping != 'N/A') or (mode == 'LEGACY_SINGLE_BYTE' and mapping in {'', 'UNBOUND', 'N/A', None}):
            errors.append(f'{name}: invalid encoding/mapping binding')
        for key in ('snapshot_size_bytes', 'application_static_memory_bytes'):
            try:
                if int(row.get(key, '')) <= 0:
                    raise ValueError()
            except ValueError:
                errors.append(f'{name}: missing positive {key}')
    return errors


if __name__ == '__main__':
    with Path(sys.argv[1]).open(encoding='utf-8-sig', newline='') as stream:
        errors = check(list(csv.DictReader(stream)))
    print('\n'.join(errors) if errors else 'PASS: runtime row structure and dispositions')
    raise SystemExit(int(bool(errors)))
