"""
Experiment identity for cached ensemble runs (issue #6, 2026-10-25).

A cached run is an .npz under results/robust_runs/, results/breakout_runs/ or results/chi0_runs/. Before this file,
a cache was found by its name (ensemble label, design, non-default solver settings) and reused without checking
what produced it, so a same-sized change to the draws, seed, ranges, solver or settings silently reused old output.

Now every run has a manifest. Its `identity` has seven parts, and a cache is reused only if all seven match the
run being requested:

    inputs         ensemble label, draw count, SHA-256 of the ordered draws (every value, exactly)
    sampling       how the draws were made: box, n, seed, the UNCERTAIN ranges, FIXED, NEAR_FRAC, the sampler's
                   source, and the PARAMS baselines the near and radius boxes centre on
    design         every lever after defaults, any extra option dict, and SHA-256 of the solver's actual input
    numerics       solver settings (T_H, nA, N), batch size, SHA-256 of the batch membership, STRIKE_TOL
    solver         SHA-256 of equilibrium_model.py and of each wrapper function on the solving path,
                   after dropping comments and blank lines (tokenize), so a comment edit keeps the cache
    dependencies   numpy version, Python major.minor
    output_schema  field names and dtypes written to the .npz

The machine (OS, CPU, commit, runner) is recorded beside the identity, not in it: cross-platform last-bit
differences are measured by `ci_sims.py repro`, not hidden by refusing to compare.

Storage: `<tag>.npz` plus `<tag>.manifest.json`, which holds the manifest and the SHA-256 of the .npz bytes.
On every load the .npz hash is checked against the manifest (content addressing) and the requested identity is
recomputed and compared part by part. A mismatch raises IdentityError naming the parts that differ. A cached
file is never overwritten.

Legacy caches (made before 2026-10-25, no manifest) are classified in results/cache_provenance.json, which pins
each file's SHA-256. Their producing identity cannot be established. Each one that maps to a current request
records the identity that request had when the inventory was taken, so a later change is still caught. It is
classified, never relabelled as verified. RD_REQUIRE_VERIFIED=1 refuses every legacy cache.

    python3 run_identity.py inventory --write   # (re)classify committed caches; refuses to change recorded hashes
    python3 run_identity.py inventory --check   # every cache file has a valid manifest or a matching inventory entry
    python3 run_identity.py show PATH           # print a cache's manifest or inventory entry

Status: implemented + verified by tests/test_run_identity.py. Not human_validated.
"""
from __future__ import annotations

import argparse
import functools
import glob
import hashlib
import inspect
import io
import json
import os
import platform
import re
import subprocess
import sys
import textwrap
import time
import tokenize

import numpy as np

SCHEMA = "offearth-run-manifest/1"
HERE = os.path.dirname(os.path.abspath(__file__))
INVENTORY = os.path.join(HERE, "results", "cache_provenance.json")
INVENTORY_MD = os.path.join(HERE, "results", "cache_provenance.md")
CACHE_DIRS = ("results/robust_runs", "results/breakout_runs", "results/chi0_runs", "diagnostics/out")
SOLVER_FILES = [os.path.join(HERE, "equilibrium_model.py")]
PARTS = ("inputs", "sampling", "design", "numerics", "solver", "dependencies", "output_schema")
# Legacy classes a solving run may reuse (with a warning). Every other class is refused for reuse.
REUSABLE_LEGACY = ("legacy_unverified", "legacy_older_schema")


class IdentityError(RuntimeError):
    """A cache or shard does not match the run being requested."""


# ---------------------------------------------------------------------------
# hashing
# ---------------------------------------------------------------------------
def canon(x):
    """JSON-ready value with floats as exact hex strings, so the hash sees every bit and nothing else."""
    if isinstance(x, (bool, np.bool_)) or x is None or isinstance(x, str):
        return bool(x) if isinstance(x, np.bool_) else x
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return "f:" + float(x).hex()
    if isinstance(x, dict):
        return {str(k): canon(v) for k, v in x.items()}
    if isinstance(x, np.ndarray):
        return [canon(v) for v in x.tolist()]
    if isinstance(x, (list, tuple)):
        return [canon(v) for v in x]
    raise TypeError(f"run_identity: cannot hash {type(x).__name__}")


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(canon(obj), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_digest(src: str) -> str:
    """SHA-256 of Python source without comments, blank lines or indentation width."""
    toks = []
    for t in tokenize.generate_tokens(io.StringIO(textwrap.dedent(src)).readline):
        if t.type in (tokenize.COMMENT, tokenize.NL):
            continue
        toks.append(f"{tokenize.tok_name[t.type]}:{t.string if t.type not in (tokenize.INDENT,) else ''}")
    return hashlib.sha256("\0".join(toks).encode()).hexdigest()


@functools.lru_cache(maxsize=None)
def _file_code_digest(path: str, mtime_ns: int, size: int) -> str:
    with open(path) as f:
        return code_digest(f.read())


def source_digest(obj) -> str:
    if isinstance(obj, str):
        st = os.stat(obj)
        return _file_code_digest(obj, st.st_mtime_ns, st.st_size)
    return code_digest(inspect.getsource(obj))


# ---------------------------------------------------------------------------
# environment (recorded, not part of the identity)
# ---------------------------------------------------------------------------
def _git(*cmd):
    try:
        return subprocess.run(["git", *cmd], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def environment() -> dict:
    env = ("RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion", "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID",
           "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW", "GITHUB_JOB")
    return dict(commit=_git("rev-parse", "HEAD"), dirty_tracked_files=bool(_git("status", "--porcelain", "-uno")),
                python=platform.python_version(), numpy=np.__version__, os=platform.platform(),
                system=platform.system(), machine=platform.machine(),
                omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
                runner={k: os.environ[k] for k in env if k in os.environ},
                utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def platform_class(env: dict) -> str:
    """Shards merged into one run must share this: same OS family, CPU architecture and numpy."""
    return f"{env.get('system')}/{env.get('machine')}/numpy {env.get('numpy')}"


# ---------------------------------------------------------------------------
# the requested identity
# ---------------------------------------------------------------------------
def _floats(d: dict) -> dict:
    return {k: (float(v) if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool) else v)
            for k, v in d.items()}


def sampling_identity(sampling: dict | None) -> dict:
    if not sampling:
        return dict(declared=False)
    import equilibrium_model as em
    import robust_design as rd
    return dict(declared=True, method="robust_design.ensemble: stratified Latin hypercube, mapped by u_to_params",
                box=sampling["box"], n=int(sampling["n"]), seed=int(sampling["seed"]),
                uncertain=[list(u) for u in rd.UNCERTAIN], fixed=_floats(rd.FIXED), near_frac=rd.NEAR_FRAC,
                baselines={u[0]: em.PARAMS[u[0]][0] for u in rd.UNCERTAIN},
                code={f.__name__: source_digest(f) for f in (rd.lhs, rd._scale_map, rd._scale_inv, rd.u_to_params,
                                                             rd.ensemble)})


def _kind_parts(kind: str, opts: dict | None):
    """Solving-path functions, default settings and output schema of each cache kind."""
    import robust_design as rd
    if kind == "robust_design":
        fns = (rd.apply_design, rd.batches_for, rd._solve_batch, rd.holds)
        fields = {k: "float64" for k in rd.KEEP} | {"act0": "<U1", "holds": "float64"}
        extra = dict(strike_tol=rd.STRIKE_TOL)
        cfg0 = rd.CFG
    elif kind == "breakout":
        import breakout_options as bo
        fns = (rd.apply_design, rd.batches_for, bo._solve)
        fields = {k: "float64" for k in bo.KEEP} | {"act0": "<U1"}
        extra = {}
        cfg0 = bo.CFG
    else:
        raise ValueError(f"run_identity: unknown kind {kind!r}")
    return fns, fields, extra, cfg0


def request(kind: str, ens_name: str, thetas, design: dict, cfg: dict, opts: dict | None = None) -> dict:
    """Manifest of the run that solving `design` over `thetas` would produce now. `thetas` may carry a
    `.sampling` dict (robust_design.ensemble sets it)."""
    import robust_design as rd
    fns, fields, extra, _ = _kind_parts(kind, opts)
    sampling = getattr(thetas, "sampling", None)
    thetas = list(thetas)
    lv = _floats(dict(rd.LEVER_BASE, **design))
    lv.setdefault("BR_mult", 1.0)
    params = [rd.apply_design(t, design) for t in thetas]
    if opts:
        params = [dict(p, **opts) for p in params]
    groups = rd.batches_for(thetas)
    ident = dict(
        inputs=dict(ensemble=ens_name, n=len(thetas), draws_sha256=digest([sorted(t.items()) for t in thetas])),
        sampling=sampling_identity(sampling),
        design=dict(levers=lv, options=_floats(opts or {}), modifiers=list(rd.MODIFIERS),
                    solver_inputs_sha256=digest([sorted(p.items()) for p in params])),
        numerics=dict(cfg=dict(cfg), batch=rd.BATCH, batches_sha256=digest([g.tolist() for g in groups]), **extra),
        solver={**{os.path.basename(f): source_digest(f) for f in SOLVER_FILES},
                **{f"{fn.__module__}.{fn.__name__}": source_digest(fn) for fn in fns}},
        dependencies=dict(numpy=np.__version__, python=".".join(platform.python_version_tuple()[:2])),
        output_schema=dict(fields=dict(sorted(fields.items()))),
    )
    spec = dict(kind=kind, ensemble=ens_name, design=_floats(design), cfg=dict(cfg), opts=_floats(opts or {}) or None,
                sampling=None if not sampling else dict(box=sampling["box"], n=int(sampling["n"]),
                                                        seed=int(sampling["seed"])))
    return dict(schema=SCHEMA, request=spec, identity=ident, identity_sha256=digest(ident),
                part_sha256={p: digest(ident[p]) for p in PARTS})


@functools.lru_cache(maxsize=64)
def _ensemble(box: str, n: int, seed: int):
    import robust_design as rd
    return rd.ensemble(box, n, seed)[1]


def rebuild(spec: dict) -> dict | None:
    """Recompute the request a manifest or inventory entry describes. None if its draws were not declared."""
    if not spec or not spec.get("sampling"):
        return None
    s = spec["sampling"]
    th = _ensemble(s["box"], s["n"], s["seed"])
    return request(spec["kind"], spec["ensemble"], th, spec["design"], spec["cfg"], spec.get("opts"))


def diff_parts(want: dict, have_parts: dict) -> list[str]:
    return [p for p in PARTS if want["part_sha256"].get(p) != have_parts.get(p)]


def _explain(want: dict, have: dict | None, parts: list[str]) -> str:
    out = []
    for p in parts:
        if have and "identity" in have and p in have["identity"]:
            a, b = have["identity"][p], want["identity"][p]
            if isinstance(a, dict) and isinstance(b, dict):
                keys = sorted(k for k in set(a) | set(b) if digest(a.get(k)) != digest(b.get(k)))
                out.append(f"{p} ({', '.join(keys[:6])}{', ...' if len(keys) > 6 else ''})")
                continue
        out.append(p)
    return "; ".join(out)


# ---------------------------------------------------------------------------
# cache files
# ---------------------------------------------------------------------------
def sidecar(path: str) -> str:
    return path[:-4] + ".manifest.json" if path.endswith(".npz") else path + ".manifest.json"


def relpath(path: str) -> str:
    return os.path.relpath(os.path.abspath(path), HERE).replace(os.sep, "/")


@functools.lru_cache(maxsize=4)
def _inventory(path: str, mtime_ns: int) -> dict:
    with open(path) as f:
        return json.load(f)


def inventory() -> dict:
    if not os.path.exists(INVENTORY):
        return dict(entries={})
    return _inventory(INVENTORY, os.stat(INVENTORY).st_mtime_ns)


def _load_npz(path: str) -> dict:
    with np.load(path) as z:
        return {k: z[k] for k in z.files}


def _warn(msg: str):
    print(f"run_identity: {msg}", file=sys.stderr, flush=True)


def describe(path: str) -> dict:
    """What is known about a cache file, after checking its bytes: a manifest (status 'verified-manifest')
    or an inventory entry (its legacy class). Raises IdentityError for an unrecorded or altered file."""
    sc = sidecar(path)
    sha = file_sha256(path)
    if os.path.exists(sc):
        with open(sc) as f:
            m = json.load(f)
        if m.get("schema") != SCHEMA:
            raise IdentityError(f"{relpath(sc)}: unknown manifest schema {m.get('schema')!r}")
        if m.get("artifact", {}).get("sha256") != sha:
            raise IdentityError(f"{relpath(path)}: bytes do not match its manifest (sha256 {sha[:12]} vs "
                                f"{str(m.get('artifact', {}).get('sha256'))[:12]}); the file was changed after it was made")
        return dict(status="manifest", manifest=m, sha256=sha)
    e = inventory()["entries"].get(relpath(path))
    if e is None:
        raise IdentityError(f"{relpath(path)} has no manifest and is not in results/cache_provenance.json, so what "
                            "produced it is unknown. It is not reused. Move it aside or re-solve it.")
    if e["sha256"] != sha:
        raise IdentityError(f"{relpath(path)}: bytes differ from the inventory (sha256 {sha[:12]} vs {e['sha256'][:12]}); "
                            "a legacy cache was replaced without a manifest")
    return dict(status=e["class"], entry=e, sha256=sha)


def load_cached(path: str, want: dict) -> dict | None:
    """The cached run at `path` if its identity equals `want`, None if there is no file. Raises IdentityError on
    any mismatch; never deletes or overwrites."""
    if not os.path.exists(path):
        if os.path.exists(sidecar(path)):
            raise IdentityError(f"{relpath(sidecar(path))} exists without its .npz")
        return None
    d = describe(path)
    if d["status"] == "manifest":
        m = d["manifest"]
        if m["identity_sha256"] != want["identity_sha256"]:
            parts = diff_parts(want, m["part_sha256"])
            raise IdentityError(f"cached {relpath(path)} was made by a different run; differs in: "
                                f"{_explain(want, m, parts)}. Not reused and not overwritten: use another --runs-dir "
                                "or move the old file aside.")
        return _load_npz(path)
    e = d["entry"]
    if os.environ.get("RD_REQUIRE_VERIFIED") == "1":
        raise IdentityError(f"{relpath(path)} is a legacy cache ({e['class']}) and RD_REQUIRE_VERIFIED=1")
    if e["class"] not in REUSABLE_LEGACY:
        raise IdentityError(f"{relpath(path)} is classified {e['class']} ({e.get('note', '')}); not reused")
    if e.get("request_identity_sha256") != want["identity_sha256"]:
        parts = diff_parts(want, e.get("request_part_sha256", {}))
        raise IdentityError(f"legacy cache {relpath(path)}: the requested run differs from the one inventoried on "
                            f"{inventory().get('taken', '?')} in: {'; '.join(parts)}. Not reused and not overwritten.")
    _warn(f"reusing legacy cache {relpath(path)} ({e['class']}): bytes match the inventory and the request matches "
          "the inventoried identity; what produced it was never recorded")
    return _load_npz(path)


def load_for_read(path: str, strict: bool = False) -> dict:
    """Load a cache for reporting. Checks its bytes, and for a manifest recomputes the declared request and
    compares identities. Legacy files are returned with their class noted on stderr (strict=True refuses them,
    as does RD_REQUIRE_VERIFIED=1)."""
    d = describe(path)
    if d["status"] == "manifest":
        m = d["manifest"]
        want = rebuild(m.get("request"))
        if want is None:
            _warn(f"{relpath(path)}: draws were not declared, so only its bytes were checked")
        elif want["identity_sha256"] != m["identity_sha256"]:
            raise IdentityError(f"{relpath(path)} is stale; its run now differs in: "
                                f"{_explain(want, m, diff_parts(want, m['part_sha256']))}")
        return _load_npz(path)
    if strict or os.environ.get("RD_REQUIRE_VERIFIED") == "1":
        raise IdentityError(f"{relpath(path)} is a legacy cache ({d['status']}); refused in strict mode")
    _LEGACY_READS.setdefault(d["status"], []).append(relpath(path))
    return _load_npz(path)


_LEGACY_READS: dict[str, list[str]] = {}


def legacy_read_summary() -> str:
    if not _LEGACY_READS:
        return ""
    return "read legacy caches whose producing identity was never recorded: " + ", ".join(
        f"{len(v)} {k}" for k, v in sorted(_LEGACY_READS.items())) + " (see results/cache_provenance.md)"


def save_cached(path: str, out: dict, want: dict, produced: dict) -> dict:
    """Write a new cache and its manifest. Refuses to overwrite either."""
    if os.path.exists(path) or os.path.exists(sidecar(path)):
        raise IdentityError(f"{relpath(path)} already exists; a cache is never overwritten")
    fields = {k: str(np.asarray(v).dtype) for k, v in out.items()}
    expect = want["identity"]["output_schema"]["fields"]
    if {k: ("<U1" if v.startswith("<U") else v) for k, v in fields.items()} != expect:
        raise IdentityError(f"{relpath(path)}: output fields {fields} do not match the declared schema {expect}")
    np.savez(path, **out)
    m = dict(want, environment=environment(), produced=produced,
             artifact=dict(file=os.path.basename(path), sha256=file_sha256(path)))
    with open(sidecar(path), "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    return m


# ---------------------------------------------------------------------------
# inventory of committed caches
# ---------------------------------------------------------------------------
_KEY_RE = re.compile(r"(?:^|_)([A-Za-z][A-Za-z0-9_]*?)=([-+0-9.eE]+|inf|nan)(?=_|$)")
_KW_RE = re.compile(r"(T_H|nA|N)(\d+)")


def parse_design_key(key: str) -> dict | None:
    if key == "base":
        return {}
    d = {m.group(1): float(m.group(2)) for m in _KEY_RE.finditer(key)}
    return d or None


def robust_spec(tag: str) -> dict | None:
    """The robust_design request a robust_runs tag names under the current code, or None."""
    import robust_design as rd
    parts = tag.split("__")
    if len(parts) not in (2, 3):
        return None
    ens, key = parts[0], parts[1]
    kw = {}
    if len(parts) == 3:
        kw = {m.group(1): int(m.group(2)) for m in _KW_RE.finditer(parts[2])}
        if "_".join(f"{k}{v}" for k, v in sorted(kw.items())) != parts[2]:
            return None
    design = parse_design_key(key)
    if design is None or rd.design_key(design) != key:
        return None
    if ens == "full":
        s = dict(box="full", n=rd.N_FULL, seed=20261016)
    elif ens == "near":
        s = dict(box="near", n=rd.N_NEAR, seed=20261017)
    elif ens == "pilotfull":
        s = dict(box="full", n=32, seed=7)
    elif ens == "pilotnear":
        s = dict(box="near", n=32, seed=8)
    elif re.fullmatch(r"r[0-9.]+", ens):
        s = dict(box=ens, n=rd.N_RAD, seed=int(1000 * float(ens[1:])) + 5)
    else:
        return None
    return dict(kind="robust_design", ensemble=ens, design=design, cfg=dict(rd.CFG, **kw), opts=None, sampling=s)


def breakout_spec(tag: str, chi0: bool) -> dict | None:
    import breakout_options as bo
    import robust_design as rd
    parts = tag.split("__")
    if len(parts) != 3 or parts[0] not in ("r0.1", "full") or parts[1] not in bo.DESIGNS:
        return None
    s = dict(box="r0.1", n=rd.N_RAD, seed=105) if parts[0] == "r0.1" else dict(box="full", n=192, seed=20261016)
    design = dict(bo.DESIGNS[parts[1]])
    if chi0:
        m = re.fullmatch(r"chi0=([-+0-9.eE]+)", parts[2])
        if not m:
            return None
        design["chi0"] = float(m.group(1))
        opts = bo.CONFIGS["off"][0]
    else:
        if parts[2] not in bo.CONFIGS:
            return None
        opts = bo.CONFIGS[parts[2]][0]
    return dict(kind="breakout", ensemble=parts[0], design=design, cfg=dict(bo.CFG), opts=dict(opts), sampling=s)


def classify(path: str) -> dict:
    rel = relpath(path)
    tag = os.path.basename(path)[:-4]
    z = _load_npz(path)
    n = len(next(iter(z.values())))
    e = dict(sha256=file_sha256(path), bytes=os.path.getsize(path), n=n, fields=sorted(z))
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if rel.startswith("diagnostics/out/"):
        return dict(e, **{"class": "reference_patched_solver",
                          "note": "made by diagnostics/noretry.py with a temporary patched copy of equilibrium_model.py; "
                                  "a reference output, not a cache of the current solver"})
    spec = (robust_spec(tag) if folder.startswith("robust_runs") else
            breakout_spec(tag, chi0=folder == "chi0_runs") if folder in ("breakout_runs", "chi0_runs") else None)
    if spec is None:
        return dict(e, **{"class": "legacy_unattributed",
                          "note": "the file name does not map to a run the current code requests"})
    want = rebuild(spec)
    e.update(request=spec, request_identity_sha256=want["identity_sha256"], request_part_sha256=want["part_sha256"])
    if n != want["identity"]["inputs"]["n"]:
        return dict(e, **{"class": "legacy_size_mismatch",
                          "note": f"{n} draws; the current request has {want['identity']['inputs']['n']}"})
    schema = want["identity"]["output_schema"]["fields"]
    if set(z) != set(schema):
        missing, extra = sorted(set(schema) - set(z)), sorted(set(z) - set(schema))
        return dict(e, **{"class": "legacy_older_schema",
                          "note": f"fields missing {missing}, extra {extra}: made by an earlier code version"})
    return dict(e, **{"class": "legacy_unverified",
                      "note": "draw count and fields match the current request; producing code, draws and "
                              "environment were not recorded"})


CLASS_TEXT = {
    "legacy_unverified": "No manifest. Draw count and output fields match the run the current code requests under "
                         "this name. What produced it (draws, solver, numpy) was never recorded. Reusable with a "
                         "warning; a request that changes after the inventory date is refused.",
    "legacy_older_schema": "As legacy_unverified, but the fields differ from the current output schema (most lack "
                           "`fail`, added 2026-10-21), so an earlier code version made it. Reusable with a warning.",
    "legacy_size_mismatch": "The draw count differs from the current request under the same name. Never reused.",
    "legacy_unattributed": "The name does not map to any run the current code requests. Never reused.",
    "reference_patched_solver": "Output of a deliberately patched solver (diagnostics/noretry.py). Never reused as a cache.",
}


def cmd_inventory(a):
    files = sorted(p for d in CACHE_DIRS for p in glob.glob(os.path.join(HERE, d, "*.npz")))
    old = inventory()["entries"]
    if a.check:
        problems, counts = [], {}
        recorded = set()
        for p in files:
            try:
                d = describe(p)
            except IdentityError as ex:
                problems.append(str(ex))
                continue
            counts[d["status"]] = counts.get(d["status"], 0) + 1
            if d["status"] != "manifest":
                recorded.add(relpath(p))
        for d in CACHE_DIRS:
            for sc in glob.glob(os.path.join(HERE, d, "*.manifest.json")):
                if not os.path.exists(sc[:-len(".manifest.json")] + ".npz"):
                    problems.append(f"{relpath(sc)} has no .npz")
        gone = sorted(set(old) - {relpath(p) for p in files})
        problems += [f"{g} is in the inventory but missing: legacy artifacts are preserved, not deleted" for g in gone]
        print(f"cache provenance: {len(files)} files: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
        for p in problems:
            print("  FAIL", p)
        sys.exit(1 if problems else 0)
    entries, kept = {}, 0
    for p in files:
        rel = relpath(p)
        if os.path.exists(sidecar(p)):
            continue
        if rel in old:
            if old[rel]["sha256"] != file_sha256(p):
                sys.exit(f"run_identity: {rel} changed since the inventory; refusing to relabel it. Restore it or "
                         "move it aside.")
            entries[rel] = old[rel]
            kept += 1
            continue
        entries[rel] = classify(p)
    counts = {}
    for e in entries.values():
        counts[e["class"]] = counts.get(e["class"], 0) + 1
    prev = inventory()
    evidence = list(prev.get("evidence", [])) + ([a.evidence] if a.evidence else [])
    if old and kept == len(entries) and not a.evidence:
        print(f"inventory unchanged ({kept} entries)")
        return
    inv = dict(schema="offearth-cache-inventory/1", taken=prev.get("taken") if old else time.strftime("%Y-%m-%d"),
               environment=prev.get("environment") if old else environment(), classes=CLASS_TEXT, counts=counts,
               entries=entries, evidence=evidence)
    with open(INVENTORY, "w") as f:
        json.dump(inv, f, indent=1, sort_keys=True)
        f.write("\n")
    write_inventory_md(inv)
    print(f"wrote {relpath(INVENTORY)}: {len(entries)} legacy entries ({kept} kept): {counts}")


def write_inventory_md(inv: dict):
    by_dir: dict[str, dict[str, list[str]]] = {}
    for rel, e in sorted(inv["entries"].items()):
        by_dir.setdefault(rel.rsplit("/", 1)[0], {}).setdefault(e["class"], []).append(rel.rsplit("/", 1)[1])
    env = inv["environment"]
    L = ["# Cache provenance inventory (auto-generated by run_identity.py inventory --write)", "",
         f"Taken {inv['taken']} at commit {str(env.get('commit'))[:12]} with Python {env['python']}, numpy {env['numpy']}, "
         f"{env['os']}{' (' + env['note'] + ')' if env.get('note') else ''}. Machine-readable copy with each file's SHA-256: `cache_provenance.json`.", "",
         "None of these files has a manifest: they were made before runs recorded their identity (issue #6). Their "
         "classes describe what can and cannot be established. **No legacy file is verified by this inventory.** "
         "Files are pinned by hash, never relabelled or overwritten. Runs made from now on carry "
         "`<tag>.manifest.json` and are not listed here.", "", "## Classes", ""]
    L += [f"- `{k}`: {v}" for k, v in inv["classes"].items()]
    L += ["", "## Counts", "", "| folder | class | files |", "|---|---|---|"]
    for d, cl in by_dir.items():
        for c, fs in sorted(cl.items()):
            L.append(f"| `{d}` | {c} | {len(fs)} |")
    L += ["", "## Files not reusable as caches", ""]
    bad = [(rel, e) for rel, e in sorted(inv["entries"].items()) if e["class"] not in REUSABLE_LEGACY]
    L += [f"- `{rel}`: {e['class']}. {e['note']}" for rel, e in bad] or ["None."]
    ev = inv.get("evidence") or []
    L += ["", "## Reproduction evidence (does not change a class)", ""]
    L += [f"- {x}" for x in ev] or ["None recorded."]
    with open(INVENTORY_MD, "w") as f:
        f.write("\n".join(L) + "\n")


def cmd_show(a):
    p = os.path.abspath(a.path)
    d = describe(p)
    print(json.dumps({k: v for k, v in d.items()}, indent=1, sort_keys=True, default=str))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inventory")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    p.add_argument("--evidence", default=None, help="with --write: append a reproduction note (never changes a class)")
    p = sub.add_parser("show")
    p.add_argument("path")
    a = ap.parse_args()
    sys.path.insert(0, HERE)
    dict(inventory=cmd_inventory, show=cmd_show)[a.cmd](a)


if __name__ == "__main__":
    main()
