"""Verify selected ordered log chunks against independent full-message oracles.

Capture JSON maps each expected case name to its ordered chunks. A chunk is a
decoded Unicode string or {"hex": "raw-byte-hex"}; raw hex avoids monitor decoding.
"""
import argparse
import json
from pathlib import Path


def check(capture, expected):
    messages = expected['messages']
    if set(capture) != set(messages):
        raise ValueError('captured case inventory differs from expected log calls')
    for name, oracle in messages.items():
        chunks = capture[name]
        if not isinstance(chunks, list) or not chunks:
            raise ValueError(f'{name}: missing ordered chunks')
        result = bytearray()
        for index, chunk in enumerate(chunks):
            raw = chunk.encode('utf-8') if isinstance(chunk, str) else bytes.fromhex(chunk['hex'])
            if not 0 < len(raw) <= expected['max_chunk_bytes']:
                raise ValueError(f'{name} chunk {index}: invalid byte length')
            raw.decode('utf-8', errors='strict')
            result.extend(raw)
        if result.hex() != oracle['hex']:
            raise ValueError(f'{name}: ordered content differs; prefix/argument/suffix may be missing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('expected', type=Path)
    args = parser.parse_args()
    try:
        check(json.loads(args.capture.read_text(encoding='utf-8')), json.loads(args.expected.read_text(encoding='utf-8')))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'FAIL: {exc}')
        raise SystemExit(1)
    print('PASS: complete ordered messages, exact suffixes, first-only substitution and bounded UTF8 chunks')
