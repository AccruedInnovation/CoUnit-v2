"""Verify captured native DiagnosticBytes as strict UTF-8 and exact bounded text."""
import argparse
import json
from pathlib import Path


def check(values, expected):
    if isinstance(values, dict):
        chunks = values['hex_chunks']
        if len(chunks) != 4 or any(not isinstance(chunk, str) or len(chunk) != 128 for chunk in chunks):
            raise ValueError('capture four 128-character DiagnosticHex chunks')
        raw = bytes.fromhex(''.join(chunks))
    else:
        raw = bytes(values)
    if len(raw) != 256:
        raise ValueError('capture exactly all 256 bytes of STRING(255) storage')
    end = raw.find(b'\0')
    if not 0 <= end <= 255:
        raise ValueError('missing bounded NUL terminator')
    logical = raw[:end]
    text = logical.decode('utf-8', errors='strict')
    if not text.endswith('...<truncated>'):
        raise ValueError('exact truncation marker missing')
    if end != expected['diagnostic_byte_count'] or logical.hex() != expected['diagnostic_hex']:
        raise ValueError('output differs from independent longest-valid-prefix oracle')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='JSON {"hex_chunks":[four DiagnosticHex strings]} or list of 256 DiagnosticBytes')
    parser.add_argument('expected', type=Path)
    args = parser.parse_args()
    try:
        check(json.loads(args.capture.read_text()), json.loads(args.expected.read_text(encoding='utf-8')))
    except (ValueError, OSError, KeyError) as exc:
        print(f'FAIL: {exc}')
        raise SystemExit(1)
    print('PASS: bounded terminator, strict UTF8, exact prefix and truncation marker')
