"""Build the dated observation table data/observations.csv from the fetched sources and batches.yaml.

    bash fetch_sources.sh && python build_observations.py [--cache .cache]

Needs the cache (network) and pyyaml. One row per (batch, model): the value public from `available` on,
its source (re-fitted from that vintage's runs, or copied from METR's published file), and the dates
that must not be confused:

    model_release_date  the model's public release (METR's x-axis for trends)
    runs_start/runs_end when the measurement runs were made (from run timestamps; empty if unknown)
    available           when this value became public (batches.yaml gives the basis)

The table is committed, so the holdout and its tests run without network.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib

import yaml

import horizon_fit as hf

HERE = pathlib.Path(__file__).resolve().parent
COLUMNS = ["record_id", "suite", "model_key", "alias", "model_release_date", "runs_start", "runs_end", "available",
           "value_source", "regularization", "p50_min", "p80_min", "p50_ci_low", "p50_ci_high", "p80_ci_low",
           "p80_ci_high", "saturated", "n_runs", "scaffolds"]


def _runs_meta(path: pathlib.Path) -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        m = meta.setdefault(r["alias"], {"model": r["model"], "t0": None, "t1": None, "n": 0, "scaffolds": set()})
        m["n"] += 1
        if r.get("scaffold"):
            m["scaffolds"].add(r["scaffold"])
        for k, f in (("started_at", min), ("completed_at", max)):
            if r.get(k):
                key = "t0" if k == "started_at" else "t1"
                m[key] = r[k] if m[key] is None else f(m[key], r[k])
    return meta


def _day(ms: float | None) -> str:
    return "" if ms is None else dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date().isoformat()


def build(cache: pathlib.Path) -> list[dict]:
    cfg = yaml.safe_load((HERE / "batches.yaml").read_text())
    pub = {s: yaml.safe_load((cache / f"metr.org/benchmark_results_1_{v}.yaml").read_text())["results"]
           for s, v in (("TH1.0", "0"), ("TH1.1", "1"))}
    final_runs = {"TH1.0": _runs_meta(cache / "vintages/th10_2026-03-05.jsonl"),
                  "TH1.1": _runs_meta(cache / "vintages/th11_2026-03-05.jsonl")}
    overrides = cfg["alias_key_overrides"]
    sat = float(cfg["saturation_minutes"])

    def key_of(suite: str, alias: str, meta: dict) -> str:
        if alias in overrides:
            return overrides[alias]
        if alias in final_runs[suite]:
            return final_runs[suite][alias]["model"]
        return meta[alias]["model"]

    rows: list[dict] = []
    fitted: dict[tuple[str, float], tuple[hf.Runs, dict]] = {}
    for b in cfg["batches"]:
        suite, src = b["suite"], b["values"]
        if src["source"] == "runs":
            vk = (src["vintage"], src["regularization"])
            if vk not in fitted:
                path = cache / f"vintages/{src['vintage']}.jsonl"
                runs = hf.load_runs(str(path), exclude_agents=())
                fitted[vk] = (hf.fit_agents(runs, src["regularization"], [a for a in set(runs.agent) if a != "human"]),
                              _runs_meta(path))
            fits, meta = fitted[vk]
            for alias in b["models"]:
                f = fits[alias]
                key = key_of(suite, alias, meta)
                m = meta[alias]
                p50 = f.horizon(0.5)
                rows.append({
                    "record_id": b["id"], "suite": suite, "model_key": key, "alias": alias,
                    "model_release_date": str(pub[suite][key]["release_date"]),
                    "runs_start": _day(m["t0"]), "runs_end": _day(m["t1"]), "available": b["available"],
                    "value_source": f"refit:{src['vintage']}", "regularization": src["regularization"],
                    "p50_min": round(p50, 6), "p80_min": round(f.horizon(0.8), 6),
                    "p50_ci_low": "", "p50_ci_high": "", "p80_ci_low": "", "p80_ci_high": "",
                    "saturated": int(p50 > sat), "n_runs": m["n"], "scaffolds": ";".join(sorted(m["scaffolds"])),
                })
        else:
            res = pub[suite]
            keys = sorted(res) if b["models"] == "all" else b["models"]
            by_key = {v["model"]: (a, v) for a, v in final_runs[suite].items()}
            by_key.update({k: (a, final_runs[suite][a]) for a, k in overrides.items() if a in final_runs[suite]})
            for key in keys:
                if suite == "TH1.1" and key in cfg["th11_stitched_from_th10"]:
                    continue
                v = res[key]["metrics"]
                alias, m = by_key.get(key, ("", None))
                rows.append({
                    "record_id": b["id"], "suite": suite, "model_key": key, "alias": alias,
                    "model_release_date": str(res[key]["release_date"]),
                    "runs_start": _day(m["t0"]) if m else "", "runs_end": _day(m["t1"]) if m else "",
                    "available": b["available"], "value_source": f"published:{src['file']}",
                    "regularization": cfg["regularization_after_correction"],
                    "p50_min": v["p50_horizon_length"]["estimate"], "p80_min": v["p80_horizon_length"]["estimate"],
                    "p50_ci_low": v["p50_horizon_length"]["ci_low"], "p50_ci_high": v["p50_horizon_length"]["ci_high"],
                    "p80_ci_low": v["p80_horizon_length"]["ci_low"], "p80_ci_high": v["p80_horizon_length"]["ci_high"],
                    "saturated": int(v["p50_horizon_length"]["estimate"] > sat), "n_runs": m["n"] if m else "",
                    "scaffolds": ";".join(sorted(str(s) for s in res[key].get("scaffolds") or [] if s)),
                })
    late = [f"{r['record_id']} {r['alias'] or r['model_key']}: runs end {r['runs_end']}, available {r['available']}"
            for r in rows if r["runs_end"] and r["runs_end"] > r["available"]]
    if late:  # the value would be dated before the runs that produced it: a leak
        raise SystemExit("measured after its availability date:\n  " + "\n  ".join(late))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(HERE / ".cache"))
    ap.add_argument("--out", default=str(HERE / "data/observations.csv"))
    a = ap.parse_args()
    rows = build(pathlib.Path(a.cache))
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
