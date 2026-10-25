"""Stale-cache and mixed-shard tests for run_identity.py (issue #6).

A deterministic stand-in replaces the solver, so the suite runs in seconds and needs no pinned numpy. Every test works
in a temporary cache folder and inventory; nothing under results/ is read or written.

    python3 tests/test_run_identity.py
"""
import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

MODEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np  # noqa: E402

import ci_sims  # noqa: E402
import robust_design as rd  # noqa: E402
import run_identity as ri  # noqa: E402

CALLS = [0]


def fake_solve_batch(args):
    """Deterministic stand-in for robust_design._solve_batch: a smooth function of the inputs and settings."""
    CALLS[0] += 1
    plist, kw = args
    x = np.array([p["g"] + p["q"] * p["d"] + p["D"] + 1e-3 * kw["nA"] for p in plist])
    out = {k: np.abs(np.sin(x * (i + 1))) for i, k in enumerate(rd.KEEP)}
    out["att"] = np.where(x > 0.9, 0.5, 0.0)
    out["act0"] = np.where(x > 1.5, "S", "C").astype("U1")
    return out


def other_solve_batch(args):
    """The same stand-in with one coefficient changed: a different solver."""
    CALLS[0] += 1
    plist, kw = args
    x = np.array([p["g"] + p["q"] * p["d"] + p["D"] + 2e-3 * kw["nA"] for p in plist])
    out = {k: np.abs(np.sin(x * (i + 1))) for i, k in enumerate(rd.KEEP)}
    out["att"] = np.where(x > 0.9, 0.5, 0.0)
    out["act0"] = np.where(x > 1.5, "S", "C").astype("U1")
    return out


def read_json(p):
    with open(p) as f:
        return json.load(f)


def write_json(p, obj):
    with open(p, "w") as f:
        json.dump(obj, f)


ARGS = "--stage oat_r --designs '[{}]'"     # one unit: r0.1__base, 64 draws, 4 batches


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rid_")
        self.saved = dict(RUNS=rd.RUNS, solve=rd._solve_batch, CFG=dict(rd.CFG), BATCH=rd.BATCH, WORKERS=rd.WORKERS,
                          STRIKE_TOL=rd.STRIKE_TOL, UNCERTAIN=list(rd.UNCERTAIN), INV=ri.INVENTORY,
                          SOLVER_FILES=list(ri.SOLVER_FILES), np_version=np.__version__)
        rd.RUNS = os.path.join(self.tmp, "robust_runs")
        os.makedirs(rd.RUNS)
        rd._solve_batch = fake_solve_batch
        rd.WORKERS = 1
        ri.INVENTORY = os.path.join(self.tmp, "inventory.json")
        ri._ensemble.cache_clear()
        CALLS[0] = 0
        os.environ.pop("RD_REQUIRE_VERIFIED", None)
        self.quiet = contextlib.redirect_stdout(io.StringIO())     # run_design prints a line per solved run
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        s = self.saved
        rd.RUNS, rd._solve_batch, rd.BATCH, rd.WORKERS, rd.STRIKE_TOL = s["RUNS"], s["solve"], s["BATCH"], s["WORKERS"], s["STRIKE_TOL"]
        rd.CFG.clear()
        rd.CFG.update(s["CFG"])
        rd.UNCERTAIN[:] = s["UNCERTAIN"]
        ri.INVENTORY, ri.SOLVER_FILES[:] = s["INV"], s["SOLVER_FILES"]
        np.__version__ = s["np_version"]
        ri._ensemble.cache_clear()
        os.environ.pop("RD_REQUIRE_VERIFIED", None)
        shutil.rmtree(self.tmp)

    def th(self, n=16, seed=105, box="r0.1"):
        return rd.ensemble(box, n, seed=seed)[1]

    def assertRefused(self, fn, *parts):
        with self.assertRaises(ri.IdentityError) as cm:
            fn()
        for p in parts:
            self.assertIn(p, str(cm.exception))
        return str(cm.exception)


class CacheReuse(Base):
    def test_identical_run_reuses(self):
        a = rd.run_design("r0.1", self.th(), {})
        n = CALLS[0]
        self.assertTrue(os.path.exists(os.path.join(rd.RUNS, "r0.1__base.manifest.json")))
        b = rd.run_design("r0.1", self.th(), {})
        self.assertEqual(CALLS[0], n, "an identical run must reuse the cache, not re-solve")
        for k in a:
            np.testing.assert_array_equal(a[k], b[k])
        # a design that spells out a baseline lever value is the same run
        self.assertEqual(rd.request_for("r0.1", self.th(), {})["identity_sha256"],
                         rd.request_for("r0.1", self.th(), dict(seq=0))["identity_sha256"])

    def test_changed_same_size_sample_is_refused(self):
        rd.run_design("r0.1", self.th(), {})
        th = self.th()
        th[3] = dict(th[3], g=th[3]["g"] * (1 + 1e-12))     # one value, last bits
        self.assertEqual(len(th), 16)
        self.assertRefused(lambda: rd.run_design("r0.1", th, {}), "inputs")

    def test_changed_seed_is_refused(self):
        rd.run_design("r0.1", self.th(), {})
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(seed=106), {}), "inputs", "sampling")

    def test_changed_range_is_refused(self):
        rd.run_design("r0.1", self.th(), {})
        j = rd.UNCERTAIN.index(next(u for u in rd.UNCERTAIN if u[0] == "g"))
        rd.UNCERTAIN[j] = ("g", 0.07, 0.8, "log", 0)
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(), {}), "sampling")

    def test_changed_solver_is_refused(self):
        rd.run_design("r0.1", self.th(), {})
        rd._solve_batch = other_solve_batch
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(), {}), "solver")

    def test_solver_file_edit_is_refused_but_comment_edit_is_not(self):
        src = os.path.join(self.tmp, "equilibrium_model.py")
        shutil.copy(ri.SOLVER_FILES[0], src)
        ri.SOLVER_FILES[:] = [src]
        rd.run_design("r0.1", self.th(), {})
        with open(src, "a") as f:
            f.write("\n# a comment changes nothing\n\n")
        n = CALLS[0]
        rd.run_design("r0.1", self.th(), {})
        self.assertEqual(CALLS[0], n)
        with open(src, "a") as f:
            f.write("TIE_TOL_EXTRA = 1e-9\n")
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(), {}), "solver")

    def test_changed_configuration_is_refused(self):
        rd.run_design("r0.1", self.th(), {})
        for name, change, undo in (
                ("nA", lambda: rd.CFG.update(nA=80), lambda: rd.CFG.update(nA=160)),
                ("batch", lambda: setattr(rd, "BATCH", 8), lambda: setattr(rd, "BATCH", 16)),
                ("strike_tol", lambda: setattr(rd, "STRIKE_TOL", 0.02), lambda: setattr(rd, "STRIKE_TOL", 0.01))):
            change()
            self.assertEqual(rd.run_tag("r0.1", {}), "r0.1__base", "the cache name does not see this change")
            self.assertRefused(lambda: rd.run_design("r0.1", self.th(), {}), "numerics")
            undo()
        rd.run_design("r0.1", self.th(), {})       # back to the original settings: reused again

    def test_changed_dependency_is_refused(self):
        rd.run_design("r0.1", self.th(), {})
        np.__version__ = "0.0.0-test"
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(), {}), "dependencies")

    def test_never_overwritten_and_tampering_detected(self):
        rd.run_design("r0.1", self.th(), {})
        path = os.path.join(rd.RUNS, "r0.1__base.npz")
        want = rd.request_for("r0.1", self.th(), {})
        self.assertRefused(lambda: ri.save_cached(path, {}, want, {}), "never overwritten")
        z = dict(np.load(path))
        z["att"] = z["att"] + 1
        np.savez(path, **z)
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(), {}), "do not match its manifest")

    def test_report_read_detects_stale_manifest(self):
        rd.run_design("r0.1", self.th(), {})
        path = os.path.join(rd.RUNS, "r0.1__base.npz")
        ri.load_for_read(path)
        rd.CFG.update(nA=80)            # the file records its own settings, so it still describes itself
        ri.load_for_read(path)
        rd._solve_batch = other_solve_batch
        self.assertRefused(lambda: ri.load_for_read(path), "stale", "solver")


class Legacy(Base):
    def legacy_file(self, n=64):
        th = self.th(n=n)
        out = rd._solve_batch(([rd.apply_design(t, {}) for t in th], rd.CFG))
        out["holds"] = rd.holds(out).astype(float)
        path = os.path.join(rd.RUNS, "r0.1__base.npz")
        np.savez(path, **out)          # the old way: no manifest
        return path

    def record(self, path):
        e = ri.classify(path)
        with open(ri.INVENTORY, "w") as f:
            json.dump(dict(taken="test", entries={ri.relpath(path): e}), f)
        return e

    def test_unrecorded_legacy_cache_is_refused(self):
        self.legacy_file()
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(n=64), {}), "not in results/cache_provenance.json")

    def test_recorded_legacy_cache_is_reused_with_warning_only_for_the_same_request(self):
        path = self.legacy_file()
        e = self.record(path)
        self.assertEqual(e["class"], "legacy_unverified")
        n = CALLS[0]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rd.run_design("r0.1", self.th(n=64), {})
        self.assertEqual(CALLS[0], n)
        self.assertIn("legacy cache", err.getvalue())
        self.assertFalse(os.path.exists(ri.sidecar(path)), "a legacy cache must not be relabelled")
        # a request that changed after the inventory is refused
        self.assertRefused(lambda: rd.run_design("r0.1", rd.ensemble("r0.1", 64, seed=7)[1], {}), "inputs")
        rd._solve_batch = other_solve_batch
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(n=64), {}), "solver")
        rd._solve_batch = fake_solve_batch
        # strict mode refuses every legacy cache
        os.environ["RD_REQUIRE_VERIFIED"] = "1"
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(n=64), {}), "RD_REQUIRE_VERIFIED")

    def test_replaced_legacy_bytes_are_refused(self):
        path = self.legacy_file()
        self.record(path)
        z = dict(np.load(path))
        z["WH"] = z["WH"] * 2
        np.savez(path, **z)
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(n=64), {}), "bytes differ from the inventory")
        self.assertRefused(lambda: ri.load_for_read(path), "bytes differ")

    def test_size_mismatch_is_classified_and_refused(self):
        path = self.legacy_file(n=16)
        e = self.record(path)
        self.assertEqual(e["class"], "legacy_size_mismatch")
        self.assertRefused(lambda: rd.run_design("r0.1", self.th(n=16), {}), "legacy_size_mismatch")


class Shards(Base):
    def solve(self, out, shard, of):
        with contextlib.redirect_stderr(io.StringIO()):
            ci_sims.cmd_solve(argparse.Namespace(args=ARGS, unit="r0.1__base", shard=shard, of=of, out=out))
        return os.path.join(out, f"r0.1__base__s{shard}of{of}")

    def merge(self, parts):
        ns = argparse.Namespace(args=ARGS, parts=parts, force=False, resolved=None,
                                manifest=os.path.join(self.tmp, "ci_manifest.json"))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
            ci_sims.cmd_merge(ns)
        return cm.exception.code

    def parts(self, name):
        d = os.path.join(self.tmp, name)
        os.makedirs(d)
        return d

    def test_complete_compatible_shards_merge_and_equal_an_unsplit_run(self):
        d = self.parts("ok")
        self.solve(d, 0, 2)
        self.solve(d, 1, 2)
        self.assertIn(self.merge(d), (0, None))
        merged = ri.load_cached(os.path.join(rd.RUNS, "r0.1__base.npz"), rd.request_for("r0.1", rd.ensemble("r0.1", rd.N_RAD, seed=105)[1], {}))
        self.assertIsNotNone(merged)
        m = read_json(os.path.join(rd.RUNS, "r0.1__base.manifest.json"))
        self.assertEqual([s["shard"] for s in m["produced"]["shards"]], [0, 1])
        rd.RUNS = os.path.join(self.tmp, "unsplit")
        os.makedirs(rd.RUNS)
        whole = rd.run_design("r0.1", rd.ensemble("r0.1", rd.N_RAD, seed=105)[1], {})
        for k in whole:
            np.testing.assert_array_equal(whole[k], merged[k])
        # the merged run is reused: planning the same stage again schedules no job
        rd.RUNS = os.path.join(self.tmp, "robust_runs")
        out = io.StringIO()
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(out):
            ci_sims.cmd_plan(argparse.Namespace(args=ARGS, shards=2, force=False))
        self.assertEqual(json.loads(out.getvalue())["include"], [])

    def test_missing_shard_is_refused(self):
        d = self.parts("missing")
        self.solve(d, 0, 2)
        self.assertIn("expected 0..1", str(self.merge(d)))

    def test_duplicate_shard_is_refused(self):
        d = self.parts("dup")
        b = self.solve(d, 0, 2)
        self.solve(d, 1, 2)
        sub = os.path.join(d, "again")
        os.makedirs(sub)
        shutil.copy(b + ".npz", sub)
        shutil.copy(b + ".json", sub)
        self.assertIn("supplied twice", str(self.merge(d)))

    def test_part_without_manifest_is_refused(self):
        d = self.parts("nomanifest")
        self.solve(d, 0, 2)
        b = self.solve(d, 1, 2)
        os.remove(b + ".json")
        self.assertIn("no shard manifest", str(self.merge(d)))

    def test_tampered_part_is_refused(self):
        d = self.parts("tampered")
        self.solve(d, 0, 2)
        b = self.solve(d, 1, 2)
        z = dict(np.load(b + ".npz"))
        z["att"] = z["att"] + 0.5
        np.savez(b + ".npz", **z)
        self.assertIn("does not match the hash", str(self.merge(d)))

    def test_incompatible_shard_is_refused(self):
        d = self.parts("incompatible")
        self.solve(d, 0, 2)
        rd.CFG.update(nA=80)                  # same unit name, other solver settings
        self.solve(d, 1, 2)
        rd.CFG.update(nA=160)
        self.assertIn("numerics", str(self.merge(d)))
        d = self.parts("otherseed")
        self.solve(d, 0, 2)
        rd._solve_batch = other_solve_batch   # same unit name, other solver
        self.solve(d, 1, 2)
        rd._solve_batch = fake_solve_batch
        self.assertIn("solver", str(self.merge(d)))

    def test_mixed_split_is_refused(self):
        d = self.parts("mixed")
        self.solve(d, 0, 2)
        self.solve(d, 1, 3)
        self.solve(d, 2, 3)
        self.assertIn("split the run differently", str(self.merge(d)))

    def test_wrong_membership_is_refused(self):
        d = self.parts("membership")
        b0 = self.solve(d, 0, 2)
        b1 = os.path.join(d, "r0.1__base__s1of2")
        shutil.copy(b0 + ".npz", b1 + ".npz")         # shard 0's draws presented as shard 1
        m = read_json(b0 + ".json")
        m["shard_manifest"]["shard"] = 1
        write_json(b1 + ".json", m)
        self.assertIn("does not hold the draws shard 1", str(self.merge(d)))

    def test_mixed_platform_is_refused(self):
        d = self.parts("platform")
        self.solve(d, 0, 2)
        b1 = self.solve(d, 1, 2)
        m = read_json(b1 + ".json")
        m["shard_manifest"]["environment"]["machine"] = "arm64-test"
        write_json(b1 + ".json", m)
        self.assertIn("different platforms", str(self.merge(d)))

    def test_cached_run_with_other_identity_stops_plan(self):
        rd.run_design("r0.1", rd.ensemble("r0.1", rd.N_RAD, seed=105)[1], {})
        rd.CFG.update(nA=80)
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(SystemExit) as cm:
            ci_sims.cmd_plan(argparse.Namespace(args=ARGS, shards=2, force=False))
        self.assertIn("numerics", str(cm.exception.code))


if __name__ == "__main__":
    unittest.main(verbosity=1)
