"""Expand variants/spec.json into solver jobs (issue #33). Stdlib only.

    python3 variants/make_jobs.py                       # write variants/jobs.json
    python3 variants/make_jobs.py --check               # fail if jobs.json is stale
    python3 variants/make_jobs.py --shards 4 DIR        # also write DIR/jobs_<k>.json for parallel runs

Every variant runs at every cap in spec['caps']: job name '<variant>@<cap>', with
solverArgs {maxiter: cap} and the variant's modelParams overrides on its preset's cached
arguments (official/run_official.mjs applies them).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = HERE / 'spec.json'
JOBS = HERE / 'jobs.json'


def expand(spec):
    jobs = []
    for v in spec['variants']:
        for cap in spec['caps']:
            job = {'name': f'{v["name"]}@{cap}', 'variant': v['name'], 'cap': cap, 'preset': v['preset'],
                   'solverArgs': {'maxiter': cap}}
            if v.get('modelParams'):
                job['modelParams'] = v['modelParams']
            jobs.append(job)
    return jobs


def shards(jobs, n):
    # Balance by solver cost, which is proportional to the cap.
    out = [[] for _ in range(n)]
    load = [0] * n
    for j in sorted(jobs, key=lambda j: -j['cap']):
        k = load.index(min(load))
        out[k].append(j)
        load[k] += j['cap']
    return out


def dump(obj):
    return '[\n' + ',\n'.join(json.dumps(j, separators=(', ', ': ')) for j in obj) + '\n]\n'


def main(argv):
    jobs = expand(json.loads(SPEC.read_text()))
    text = dump(jobs)
    if argv[:1] == ['--check']:
        if not JOBS.exists() or JOBS.read_text() != text:
            sys.exit('variants/jobs.json is stale: run python3 variants/make_jobs.py')
        print(f'variants/jobs.json up to date ({len(jobs)} jobs)')
        return
    JOBS.write_text(text)
    print(f'wrote {JOBS} ({len(jobs)} jobs)')
    if argv[:1] == ['--shards']:
        n, d = int(argv[1]), Path(argv[2])
        d.mkdir(parents=True, exist_ok=True)
        for k, part in enumerate(shards(jobs, n)):
            (d / f'jobs_{k}.json').write_text(dump(part))
        print(f'wrote {n} shards to {d}')


if __name__ == '__main__':
    main(sys.argv[1:])
