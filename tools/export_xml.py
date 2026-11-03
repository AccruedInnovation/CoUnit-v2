"""Export the current callable v2 source closure with the existing PLCOpenXML writer.

This adapts CoUnit's unprefixed export filenames to the repository writer. It
does not open an IDE or synchronize a native package implicitly.
"""
from __future__ import annotations

import argparse
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / '_tools'), str(ROOT / 'qualification')]
import generate_plcopenxml as plc
from check_public_api import uncomment

KINDS = {'FUNCTION_BLOCK': 'POU', 'FUNCTION': 'POU', 'PROGRAM': 'POU',
         'TYPE': 'DUT', 'VAR_GLOBAL': 'GVL', 'INTERFACE': 'I'}


def source_objects(source=ROOT / 'PlaintextExport'):
    objects = {}
    for path in sorted(source.rglob('*.DEC.exp')):
        declaration = path.read_text(encoding='utf-8-sig')
        code = re.sub(r'\{[^}]*\}', '', uncomment(declaration)).strip()
        kind = code.split()[0].upper() if code else ''
        if kind not in KINDS:
            continue
        name = path.parent.name
        if path.name != name + '.DEC.exp':
            raise ValueError('Unexpected canonical export filename: ' + str(path))
        key = name.casefold()
        if key in objects:
            raise ValueError('Duplicate source object: ' + name)
        implementation = path.with_name(name + '.IMP.exp')
        obj = plc.ObjectExport(KINDS[kind], name, declaration,
                              implementation.read_text(encoding='utf-8-sig') if implementation.exists() else None,
                              tuple(path.parent.parent.relative_to(source).parts), path)
        for child in sorted(path.parent.glob('*/*.DEC.exp')):
            text = child.read_text(encoding='utf-8-sig')
            member_code = re.sub(r'\{[^}]*\}', '', uncomment(text)).strip()
            if not member_code.upper().startswith('METHOD '):
                # The v2 closure has methods only; obsolete property-based writers
                # are never silently flattened into methods.
                continue
            imp = child.with_name(child.parent.name + '.IMP.exp')
            obj.members.append(plc.Member('M', child.parent.name, text,
                                          imp.read_text(encoding='utf-8-sig') if imp.exists() else None, child))
        obj.object_id = str(uuid.uuid5(plc.UUID_NAMESPACE, 'counit:' + key))
        for member in obj.members:
            member.object_id = str(uuid.uuid5(plc.UUID_NAMESPACE, 'counit:' + key + ':' + member.name.casefold()))
        objects[key] = obj
    return objects


def active_objects(source=ROOT / 'PlaintextExport'):
    objects = source_objects(source)
    roots = {'fb_testsuite', 'fb_testresults', 'fb_counitfixture', 'fb_counitexpectation', 'fb_testscantrace', 'write_device_log', 'bind_legacy_results', 'configure_legacy_run'}
    roots.update(key for key in objects if key.startswith(('test', 'is_test', 'run', 'counit_')))
    pending, seen = list(roots & objects.keys()), set()
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        seen.add(key)
        obj = objects[key]
        text = '\n'.join([obj.declaration, obj.implementation or ''] +
                         [m.declaration + '\n' + (m.implementation or '') for m in obj.members])
        code = re.sub(r"'(?:\$[^\r\n]|[^'])*'", '', uncomment(text))
        pending.extend({word.casefold() for word in re.findall(r'\b[A-Za-z_]\w*\b', code)} & objects.keys() - seen)
    return [objects[key] for key in sorted(seen)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    objects = active_objects()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    plc.build_xml(objects, 'CoUnit 2.1 candidate').write(args.output, encoding='utf-8', xml_declaration=True)
    print(f'Exported {len(objects)} objects to {args.output}')


if __name__ == '__main__':
    main()
