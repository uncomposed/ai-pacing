"""Summaries and tolerance checks for the AI Futures Model replication.

No import of the upstream model: this module only reads rollout records and committed
JSON, so the fast tests can run it under the repository's pinned CI Python.

Statistic definitions follow upstream at the pinned commit
(scripts/export/generate_overlay_distributions.py and
scripts/plotting_utils/rollouts_reader.py):

- a rollout counts when its record has a `results` dict (failed rollouts are dropped);
- a milestone is achieved when results.milestones[name].time is finite;
- unachieved rollouts are placed at the simulation end before taking quantiles;
- p10/p50/p90 are numpy.quantile with the default (linear) method.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence

import numpy as np

OVERLAY_MILESTONES = (
    "AC",
    "AI2027-SC",
    "SAR-level-experiment-selection-skill",
    "SIAR-level-experiment-selection-skill",
    "TED-AI",
    "ASI",
)
QUANTILES = (0.1, 0.5, 0.9)


def iter_rollout_records(path: Path) -> Iterator[dict]:
    """Yield the compact part of each usable rollout record in a rollouts.jsonl file."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            res = rec.get("results")
            if not isinstance(res, dict):
                continue
            times = res.get("times") or []
            yield {
                "sample_id": rec.get("sample_id"),
                "ac_anchor_mode": (rec.get("parameters") or {}).get("ac_anchor_mode"),
                "sim_end": float(times[-1]) if len(times) else None,
                "milestones": {
                    name: _finite_or_none((res.get("milestones") or {}).get(name, {}).get("time"))
                    for name in OVERLAY_MILESTONES
                },
            }


def failure_reasons(path: Path) -> Dict[str, int]:
    """Count rollouts without results by (anchor mode, first words of the error)."""
    counts: Dict[str, int] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                counts["unparseable line"] = counts.get("unparseable line", 0) + 1
                continue
            if isinstance(rec.get("results"), dict):
                continue
            err = str(rec.get("error"))
            kind = "timeout" if "timed out" in err else ("infeasible uplift belief" if "could not find" in err else err[:60])
            key = f"{(rec.get('parameters') or {}).get('ac_anchor_mode')}: {kind}"
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _finite_or_none(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def milestone_stats(records: Sequence[dict], name: str) -> dict:
    """Upstream-style statistics for one milestone over a list of compact records."""
    achieved = [r["milestones"][name] for r in records if r["milestones"].get(name) is not None]
    n_not = len(records) - len(achieved)
    ends = [r["sim_end"] for r in records if r["sim_end"] is not None]
    sim_end = float(np.median(ends)) if ends else None
    data = np.asarray(achieved, dtype=float)
    if n_not and sim_end is not None:
        data = np.concatenate([data, np.full(n_not, sim_end)])
    out = {
        "num_achieved": len(achieved),
        "num_not_achieved": n_not,
        "total_rollouts": len(records),
        "achievement_rate_pct": 100.0 * len(achieved) / len(records) if records else None,
    }
    if data.size:
        q = np.quantile(data, QUANTILES)
        out.update({"p10": float(q[0]), "p50": float(q[1]), "p90": float(q[2])})
    return out


def bootstrap_quantile_se(records: Sequence[dict], name: str, n_boot: int = 400, seed: int = 0) -> Dict[str, float]:
    """Bootstrap standard errors of p10/p50/p90 for one milestone (deterministic seed)."""
    rng = np.random.default_rng(seed)
    ends = [r["sim_end"] for r in records if r["sim_end"] is not None]
    sim_end = float(np.median(ends)) if ends else np.nan
    vals = np.array([r["milestones"][name] if r["milestones"].get(name) is not None else sim_end for r in records])
    if vals.size < 2:
        return {}
    idx = rng.integers(0, vals.size, size=(n_boot, vals.size))
    qs = np.quantile(vals[idx], QUANTILES, axis=1)
    return {f"p{int(q * 100)}": float(np.std(qs[i], ddof=1)) for i, q in enumerate(QUANTILES)}


def summarize(records: Sequence[dict], by_mode: bool = True) -> dict:
    out = {"overall": {}, "by_mode": {}}
    for m in OVERLAY_MILESTONES:
        s = milestone_stats(records, m)
        s["bootstrap_se"] = bootstrap_quantile_se(records, m)
        out["overall"][m] = s
    if by_mode:
        modes = sorted({r["ac_anchor_mode"] for r in records if r["ac_anchor_mode"]})
        for mode in modes:
            sub = [r for r in records if r["ac_anchor_mode"] == mode]
            out["by_mode"][mode] = {m: milestone_stats(sub, m) for m in OVERLAY_MILESTONES}
    return out


def read_published_overlay(csv_path: Path) -> Dict[str, dict]:
    """Read upstream's milestone_pdfs_overlay_statistics.csv."""
    import csv

    rows = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["milestone_name"]] = {
                "num_achieved": int(r["num_achieved"]),
                "num_not_achieved": int(r["num_not_achieved"]),
                "total_rollouts": int(r["total_rollouts"]),
                "achievement_rate_pct": float(r["achievement_rate_pct"]),
                "p10": float(r["p10"]),
                "p50": float(r["p50"]),
                "p90": float(r["p90"]),
            }
    return rows


def compare_to_published(ours: dict, published: Dict[str, dict], z: float) -> List[dict]:
    """Compare quantiles and achievement rates with a stated sampling tolerance.

    For each quantile: pass when |ours - published| <= z * sqrt(se_ours^2 + se_pub^2), with
    se_ours the bootstrap SE of our sample and se_pub = se_ours * sqrt(n_ours / n_pub) (the
    published run's raw draws are not available, so its SE is scaled from ours). For the
    achievement rate: pass when the difference is within z binomial standard errors of the
    pooled rate. The tolerance covers sampling noise only; it does not cover code drift.
    """
    rows = []
    for name, pub in published.items():
        if name not in ours:
            continue
        o = ours[name]
        n_o, n_p = o["total_rollouts"], pub["total_rollouts"]
        for q in ("p10", "p50", "p90"):
            se_o = o.get("bootstrap_se", {}).get(q)
            if se_o is None or q not in o:
                continue
            se_p = se_o * math.sqrt(n_o / n_p)
            tol = z * math.sqrt(se_o ** 2 + se_p ** 2)
            diff = o[q] - pub[q]
            rows.append({"milestone": name, "stat": q, "ours": o[q], "published": pub[q],
                         "diff": diff, "tolerance": tol, "pass": abs(diff) <= tol})
        p_o, p_p = o["achievement_rate_pct"] / 100.0, pub["achievement_rate_pct"] / 100.0
        pooled = (p_o * n_o + p_p * n_p) / (n_o + n_p)
        se = math.sqrt(max(pooled * (1 - pooled), 1e-12) * (1 / n_o + 1 / n_p))
        diff = 100.0 * (p_o - p_p)
        rows.append({"milestone": name, "stat": "achievement_rate_pct", "ours": 100 * p_o, "published": 100 * p_p,
                     "diff": diff, "tolerance": 100.0 * z * se, "pass": abs(diff) <= 100.0 * z * se})
    return rows


def max_rel_diff(a: Iterable[float], b: Iterable[float], floor: float = 1e-300) -> float:
    """Largest |a-b| / max(|b|, floor) over paired finite entries; inf on a finite/non-finite mismatch."""
    a = np.asarray(list(a), dtype=float)
    b = np.asarray(list(b), dtype=float)
    if a.shape != b.shape:
        return float("inf")
    fa, fb = np.isfinite(a), np.isfinite(b)
    if np.any(fa != fb):
        return float("inf")
    if not np.any(fa):
        return 0.0
    return float(np.max(np.abs(a[fa] - b[fb]) / np.maximum(np.abs(b[fb]), floor)))


def crossing_time(times: Sequence[float], values: Sequence[float], level: float) -> Optional[float]:
    """First time a non-decreasing series reaches `level`, by linear interpolation; None if never."""
    t = np.asarray(times, dtype=float)
    v = np.asarray(values, dtype=float)
    hit = np.nonzero(v >= level)[0]
    if hit.size == 0:
        return None
    i = int(hit[0])
    if i == 0:
        return float(t[0])
    v0, v1 = v[i - 1], v[i]
    if v1 == v0:
        return float(t[i])
    return float(t[i - 1] + (level - v0) * (t[i] - t[i - 1]) / (v1 - v0))
