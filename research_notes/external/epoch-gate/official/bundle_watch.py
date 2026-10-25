"""Compare a freshly downloaded GATE playground bundle with the pin (issue #33). Stdlib only.

    python3 official/bundle_watch.py <fresh-meta.json> [<report.md>] [data/bundle_pin.json]

<fresh-meta.json> is the output of `node official/bundle_meta.mjs <gate.js> <out.json>` on
the bundle as served now. The pin, data/bundle_pin.json, is the same extraction of the
pinned bundle (sha256 c2104290...). Prints a Markdown report (and writes it to
<report.md> if given): the old and new hash and size, and every difference in the
parameter table and in the three presets' arguments. Exit status 0 when the hash is
unchanged, 1 when it changed (a redeploy: record it as a finding in README.md with the
date, the new hash and this report; do not edit the pin to make the check pass), 2 when
the fresh bundle could not be parsed.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PIN = HERE / 'data' / 'bundle_pin.json'


def flatten(obj, prefix=''):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out.update(flatten(v, f'{prefix}.{k}' if prefix else k))
        return out
    return {prefix: obj}


def keyed_table(rows):
    out = {}
    for r in rows or []:
        key = r.get('Variable in code') or r.get('Parameter name')
        if r.get('Variable in code') == 'beliefs.train_reqs_beliefs':
            key = f'{key} ({r.get("Parameter name")})'  # two rows share this variable
        out[key] = r
    return out


def diff_tables(old, new):
    lines = []
    a, b = keyed_table(old), keyed_table(new)
    for k in sorted(set(a) - set(b)):
        lines.append(f'- removed parameter `{k}`')
    for k in sorted(set(b) - set(a)):
        lines.append(f'- added parameter `{k}`: {json.dumps(b[k], ensure_ascii=False)}')
    for k in [k for k in a if k in b]:
        for f in sorted(set(a[k]) | set(b[k])):
            if a[k].get(f) != b[k].get(f):
                lines.append(f'- `{k}` {f}: {a[k].get(f)!r} -> {b[k].get(f)!r}')
    if [k for k in a if k in b] != [k for k in b if k in a]:
        lines.append('- parameter order changed')
    return lines


def diff_presets(old, new):
    lines = []
    old, new = old or [], new or []
    if len(old) != len(new):
        lines.append(f'- number of presets {len(old)} -> {len(new)}')
    for i in range(max(len(old), len(new))):
        a = flatten(old[i]) if i < len(old) else {}
        b = flatten(new[i]) if i < len(new) else {}
        for k in sorted(set(a) | set(b)):
            if a.get(k, '<absent>') != b.get(k, '<absent>'):
                lines.append(f'- preset {i} `{k}`: {json.dumps(a.get(k, "<absent>"))} -> {json.dumps(b.get(k, "<absent>"))}')
    return lines


def compare(pin, fresh):
    changed = pin['sha256'] != fresh['sha256']
    L = ['# GATE playground bundle check', '']
    L.append(f'- pinned: `{pin["sha256"]}` ({pin["bytes"]} bytes)')
    L.append(f'- served: `{fresh["sha256"]}` ({fresh["bytes"]} bytes)')
    L.append(f'- verdict: {"**REDEPLOYED** (hash changed)" if changed else "unchanged"}')
    if fresh.get('errors'):
        L.append(f'- extraction errors on the served bundle: {fresh["errors"]}')
    L.append('')
    t = diff_tables(pin['parameter_table'], fresh['parameter_table'])
    p = diff_presets(pin['presets'], fresh['presets'])
    L.append('## Parameter table (`input_default2`)')
    L.append('')
    L.extend(t or ['- no differences'])
    L.append('')
    L.append('## Presets (`cache_default[*].args`)')
    L.append('')
    L.extend(p or ['- no differences'])
    L.append('')
    if changed and not t and not p and not fresh.get('errors'):
        L.append('The hash changed but the parameter table and presets did not: the change is in the solver, '
                 'the cached runs or the page code. Rerun the epoch-gate workflow to see whether outputs moved.')
        L.append('')
    return changed, '\n'.join(L)


def main(argv):
    if not argv:
        sys.exit(__doc__)
    fresh = json.loads(Path(argv[0]).read_text())
    pin = json.loads(Path(argv[2]).read_text() if len(argv) > 2 else PIN.read_text())
    changed, report = compare(pin, fresh)
    print(report)
    if len(argv) > 1:
        Path(argv[1]).write_text(report)
    if fresh.get('errors') and changed:
        sys.exit(2)
    sys.exit(1 if changed else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
