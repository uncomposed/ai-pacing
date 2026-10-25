"""Independent re-implementation of METR's per-agent time-horizon fit (numpy only).

METR (eval-analysis-public, src/horizon/utils/logistic.py and wrangle/{logistic,bootstrap}.py at the
pinned commit) fits, for each agent separately,

    P(success | task) = sigmoid(a + b * log2(human_minutes))

by scikit-learn's LogisticRegression(C = 1/regularization) with per-run sample weights. scikit-learn's
L2 objective penalises the slope only:

    minimise  C * sum_i w_i * BCE(y_i, p_i) + 0.5 * b**2

The p-percent horizon is the human time at which the fitted curve crosses p:

    h_p = 2 ** ((logit(p) - a) / b)       [minutes]

Here the same objective is minimised by damped Newton iteration to a tight gradient tolerance, so it
does not depend on scikit-learn's solver or its stopping rule. Fractional scores (not used by the
headline fit, which uses score_binarized) enter BCE directly, which is the same objective as METR's
split into weighted 0s and 1s.

The hierarchical bootstrap (task_family -> task_id -> run_id, all agents resampled together, one
generator per replicate seeded 42 + i) mirrors upstream's bootstrap_sample() step by step, including
the order of random draws, so that with the same numpy version it draws the same index sets.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

LOGIT = {p: math.log(p / (1 - p)) for p in (0.5, 0.8)}


@dataclass(frozen=True)
class Fit:
    intercept: float
    slope: float
    iterations: int
    grad_norm: float

    def horizon(self, p: float) -> float:
        """Human-minutes at which the fitted success probability equals p."""
        if self.slope == 0.0:
            return float("nan")
        return float(2.0 ** ((math.log(p / (1 - p)) - self.intercept) / self.slope))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _objective(theta: np.ndarray, x: np.ndarray, y: np.ndarray, w: np.ndarray, c: float) -> float:
    z = theta[0] + theta[1] * x
    # BCE with logits, numerically stable: log(1+e^z) - y z
    bce = np.logaddexp(0.0, z) - y * z
    return float(c * np.dot(w, bce) + 0.5 * theta[1] ** 2)


def fit_logistic(
    log2_minutes: Sequence[float],
    y: Sequence[float],
    weights: Sequence[float],
    regularization: float,
    *,
    tol: float = 1e-8,
    max_iter: int = 200,
) -> Fit:
    """Minimise C * sum w_i BCE_i + b^2 / 2 with C = 1/regularization (intercept unpenalised)."""
    x = np.asarray(log2_minutes, dtype=float)
    yy = np.asarray(y, dtype=float)
    w = np.asarray(weights, dtype=float)
    if not (x.shape == yy.shape == w.shape) or x.ndim != 1:
        raise ValueError("x, y and weights must be 1-D arrays of equal length")
    if np.any((yy < 0) | (yy > 1)):
        raise ValueError("y must lie in [0, 1]")
    c = 1.0 / regularization
    # Start at the weighted mean success rate with zero slope.
    ybar = float(np.clip(np.dot(w, yy) / w.sum(), 1e-6, 1 - 1e-6))
    theta = np.array([math.log(ybar / (1 - ybar)), 0.0])
    f = _objective(theta, x, yy, w, c)
    gnorm = float("inf")
    for it in range(1, max_iter + 1):
        p = _sigmoid(theta[0] + theta[1] * x)
        r = c * w * (p - yy)
        grad = np.array([r.sum(), np.dot(r, x) + theta[1]])
        gnorm = float(np.max(np.abs(grad)) / max(1.0, c * w.sum()))
        if gnorm < tol:
            return Fit(float(theta[0]), float(theta[1]), it, gnorm)
        s = c * w * p * (1 - p)
        hess = np.array([[s.sum(), np.dot(s, x)], [np.dot(s, x), np.dot(s, x * x) + 1.0]])
        step = np.linalg.solve(hess, grad)
        # Converged when the full Newton step no longer moves the parameters (float floor).
        if float(np.max(np.abs(step))) < 1e-6 * (1.0 + float(np.max(np.abs(theta)))):
            return Fit(float(theta[0]), float(theta[1]), it, gnorm)
        t = 1.0
        while True:
            cand = theta - t * step
            fc = _objective(cand, x, yy, w, c)
            if fc <= f - 1e-4 * t * float(np.dot(grad, step)):
                break
            t *= 0.5
            if t < 1e-12:
                if gnorm < 1e-6:  # objective flat to rounding; accept
                    return Fit(float(theta[0]), float(theta[1]), it, gnorm)
                raise RuntimeError(f"line search failed (grad {gnorm:.3g})")
        theta, f = cand, fc
    raise RuntimeError(f"Newton did not converge in {max_iter} iterations (grad {gnorm:.3g}, theta {theta}, step {step})")


# ---------------------------------------------------------------------------------------------
# Runs


@dataclass
class Runs:
    """Columns of a METR runs.jsonl file (one row per run), as numpy arrays."""

    agent: np.ndarray
    task_family: np.ndarray
    task_id: np.ndarray
    run_id: np.ndarray
    human_minutes: np.ndarray
    score: np.ndarray
    weight: np.ndarray

    def __len__(self) -> int:
        return len(self.agent)

    def take(self, idx: np.ndarray) -> "Runs":
        return Runs(*(getattr(self, f)[idx] for f in self.__dataclass_fields__))


def load_runs(path: str, weight_col: str = "invsqrt_task_weight", score_col: str = "score_binarized",
              exclude_agents: Iterable[str] = ("human",)) -> Runs:
    excl = set(exclude_agents)
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                rows.append(r)
    keep = [r for r in rows if r["alias"] not in excl]
    return Runs(
        agent=np.array([r["alias"] for r in keep], dtype=object),
        task_family=np.array([r["task_family"] for r in keep], dtype=object),
        task_id=np.array([r["task_id"] for r in keep], dtype=object),
        run_id=np.array([r["run_id"] for r in keep], dtype=object),
        human_minutes=np.array([float(r["human_minutes"]) for r in keep]),
        score=np.array([float(r[score_col]) for r in keep]),
        weight=np.array([float(r[weight_col]) for r in keep]),
    )


def fit_agents(runs: Runs, regularization: float, agents: Iterable[str] | None = None) -> dict[str, Fit]:
    """Point fit per agent. Upstream returns zeros when an agent never succeeds; we return None."""
    out: dict[str, Fit] = {}
    for a in sorted(set(runs.agent) if agents is None else agents):
        m = runs.agent == a
        y = runs.score[m]
        if not np.any(y > 0):
            continue
        out[a] = fit_logistic(np.log2(runs.human_minutes[m]), y, runs.weight[m], regularization)
    return out


# ---------------------------------------------------------------------------------------------
# Hierarchical bootstrap, mirroring upstream bootstrap_sample(categories=[task_family, task_id, run_id])


def _unique_inverse(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # np.unique on object arrays of str sorts lexicographically, like upstream (pandas -> numpy objects).
    u, inv = np.unique(values.astype(str), return_inverse=True)
    return u, inv.reshape(-1)


def bootstrap_indices(runs: Runs, rng: np.random.Generator, levels: str = "ftr") -> np.ndarray:
    """One hierarchical resample. `levels` picks the hierarchy, in upstream's letters: f task family,
    t task, r run within (task, agent). The default "ftr" is what upstream's headline bootstrap uses; other
    values exist only to test what each level contributes to the interval width."""
    if not levels or any(c not in "ftr" for c in levels) or list(levels) != sorted(set(levels), key="ftr".index):
        raise ValueError(f"levels must be a non-empty subsequence of 'ftr', got {levels!r}")
    cats = [c for c, on in ((runs.task_family, "f" in levels), (runs.task_id, "t" in levels)) if on]
    indices = np.arange(len(runs))
    split_ids = np.zeros(len(runs), dtype=np.int32)
    new_split_id = 0
    for i, cat in enumerate(cats):
        last = i == len(cats) - 1
        new_idx, new_split = [], []
        for gid in np.unique(split_ids):
            gidx = indices[split_ids == gid]
            _, vinv = _unique_inverse(cat[gidx])
            n = int(vinv.max()) + 1
            sampled = rng.choice(n, size=n, replace=True)
            for j, sv in enumerate(sampled):
                sidx = gidx[vinv == sv]
                new_idx.append(sidx)
                if not last:
                    new_split.append(np.full(len(sidx), new_split_id + j))
            new_split_id += n
        indices = np.concatenate(new_idx)
        if not last:
            split_ids = np.concatenate(new_split)
    if "r" not in levels:
        return indices
    # run level: resample runs within each (task_id, agent) group
    key = np.char.add(np.char.add(runs.task_id.astype(str), "|||"), runs.agent.astype(str))[indices]
    _, kinv, counts = np.unique(key, return_inverse=True, return_counts=True)
    kinv = kinv.reshape(-1)
    rnd = rng.random(len(indices))
    offsets = np.cumsum([0] + list(counts)[:-1])
    parts = [indices[kinv == j][(rnd[o:o + c] * c).astype(np.int64)] for j, (c, o) in enumerate(zip(counts, offsets))]
    return np.concatenate(parts)


def bootstrap_horizons(runs: Runs, regularization: float, n: int, percents: Sequence[float] = (0.5, 0.8),
                       seed0: int = 42, levels: str = "ftr") -> dict[str, np.ndarray]:
    """Replicate b uses default_rng(seed0 + b). Returns {agent: array (n, len(percents))} with NaN where
    a replicate had no variation in y (upstream skips those)."""
    agents = sorted(set(runs.agent))
    out = {a: np.full((n, len(percents)), np.nan) for a in agents}
    for b in range(n):
        rng = np.random.default_rng(seed0 + b)
        s = runs.take(bootstrap_indices(runs, rng, levels))
        for a in agents:
            m = s.agent == a
            y = s.score[m]
            if m.sum() == 0 or len(np.unique(y)) < 2:
                continue
            f = fit_logistic(np.log2(s.human_minutes[m]), y, s.weight[m], regularization)
            out[a][b] = [f.horizon(p) for p in percents]
    return out
