"""Compare the 60 R3-preserved declarations without freezing private storage.

This is a drift check; a real unchanged downstream native compile is still required.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent if (HERE.parent / 'docs').is_dir() else HERE.parents[3]
INVENTORY = REPO / 'docs/CoUnit-PRD-Suite-R3/PRD-COU-04/qualification/public-api-surface.csv'
BASELINE = (REPO / 'compatibility/1.2.0.3' if (REPO / 'compatibility').is_dir() else HERE.parents[1] / '1.2.0.3') / 'PlaintextExport/Unit Test Framework for CODESYS'
CANDIDATE = HERE.parent / 'PlaintextExport/Unit Test Framework for CODESYS'


def uncomment(text: str) -> str:
    # IEC strings may contain // or (*, so comments must be lexed, not stripped blindly.
    tokens = re.compile(r"'(?:\$[^\r\n]|[^']|'')*'|\"(?:\$[^\r\n]|[^\"]|\"\")*\"|\(\*|//", re.S)
    result, pos = [], 0
    while match := tokens.search(text, pos):
        result.append(text[pos:match.start()])
        token = match.group()
        if token == '(*':
            end = text.find('*)', match.end())
            if end < 0:
                raise ValueError('unterminated declaration comment')
            pos = end + 2
        elif token == '//':
            end = text.find('\n', match.end())
            pos = len(text) if end < 0 else end
        else:
            result.append(token)
            pos = match.end()
    return ''.join(result) + text[pos:]


def canonical(text: str) -> str:
    # Ignore formatting and identifier case; retain case inside string constants.
    tokens = re.findall(r"'(?:\$[^\r\n]|[^']|'')*'|\"(?:[^\"]|\"\")*\"|[A-Za-z_]\w*|\d+|[^\s]", text)
    return ' '.join(token if token.startswith(("'", '"')) else token.upper() for token in tokens)


def signature(text: str, kind: str) -> str:
    text = uncomment(text)
    text = re.sub(r'\{[^}]*\}', '', text)
    if kind in {'type', 'global_constants', 'interface'}:
        return canonical(text)
    # Public call/inheritance contract includes input, output and in-out sections;
    # ordinary VAR, VAR_TEMP, VAR_STAT and private initializers are implementation.
    header = re.split(r'\bVAR(?:_\w+)?\b', text, maxsplit=1, flags=re.I)[0]
    blocks = re.findall(r'\b(VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT)\b(.*?)\bEND_VAR\b', text, re.S | re.I)
    return canonical(header + ''.join(f'{scope} {body} END_VAR' for scope, body in blocks))


def check(baseline: Path, candidate: Path, inventory: Path = INVENTORY) -> list[str]:
    with inventory.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    errors = []
    identities = {(row['symbol'], row['kind']) for row in rows}
    if len(rows) != 60 or len(identities) != 60:
        errors.append('inventory must contain 60 unique preserved declarations')
    for row in rows:
        old, new = baseline / row['source_path'], candidate / row['source_path']
        if not old.is_file() or not new.is_file():
            errors.append(f"{row['symbol']}: missing baseline or candidate declaration")
            continue
        before = signature(old.read_text(encoding='utf-8-sig'), row['kind'])
        after = signature(new.read_text(encoding='utf-8-sig'), row['kind'])
        # User-approved 2026-09-09: aggregate case counters must represent 32*2048.
        # Permit only these three UINT -> UDINT changes, not arbitrary type drift.
        if row['symbol'] == 'ST_TestSuiteResults':
            for field in ('NumberOfTestCases', 'NumberOfSuccessfulTestCases', 'NumberOfFailedTestCases'):
                after = after.replace(f'{field.upper()} : UDINT ;', f'{field.upper()} : UINT ;')
        if before != after:
            errors.append(f"{row['symbol']}: public declaration drift\n  baseline: {before}\n  candidate: {after}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--candidate', type=Path, default=CANDIDATE)
    args = parser.parse_args()
    errors = check(args.baseline, args.candidate)
    print('\n'.join(errors) if errors else 'PASS: 60 preserved public declarations match; private storage excluded')
    print('Native unchanged-consumer compatibility is a separate required observation.')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
