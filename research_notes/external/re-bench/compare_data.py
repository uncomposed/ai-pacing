#!/usr/bin/env python3
"""Compare a rebuilt data/ directory with the committed one: numbers within a relative tolerance, text exactly.

    python3 compare_data.py NEW_DIR [REF_DIR] [--rel 1e-9]

Used by .github/workflows/re-bench-repro.yml. Exact text diffs are avoided on purpose: floating-point
formatting can move the last digit between platforms, while a real change still fails. [[ai gen]]
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path


def is_num(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def same(a, b, rel, path):
    if isinstance(b, dict):
        assert isinstance(a, dict) and a.keys() == b.keys(), f'{path}: keys differ'
        for k in b:
            same(a[k], b[k], rel, f'{path}.{k}')
    elif isinstance(b, list):
        assert isinstance(a, list) and len(a) == len(b), f'{path}: lengths differ'
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, rel, f'{path}[{i}]')
    elif isinstance(b, bool) or b is None or not is_num(b) or not is_num(a):
        assert a == b, f'{path}: {a!r} != {b!r}'
    else:
        assert math.isclose(float(a), float(b), rel_tol=rel, abs_tol=1e-12), f'{path}: {a!r} vs {b!r}'


def load(path):
    if path.suffix == '.json':
        return json.loads(path.read_text(encoding='utf-8'))
    return list(csv.DictReader(path.read_text(encoding='utf-8').splitlines()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('new', type=Path)
    ap.add_argument('ref', type=Path, nargs='?', default=Path(__file__).resolve().parent / 'data')
    ap.add_argument('--rel', type=float, default=1e-9)
    a = ap.parse_args()
    names = sorted(p.name for p in a.ref.iterdir() if p.suffix in ('.csv', '.json'))
    assert names == sorted(p.name for p in a.new.iterdir() if p.suffix in ('.csv', '.json')), 'file sets differ'
    for n in names:
        same(load(a.new / n), load(a.ref / n), a.rel, n)
    print(f'compare_data: {len(names)} files match the committed data/ (numbers within {a.rel:g} relative)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
