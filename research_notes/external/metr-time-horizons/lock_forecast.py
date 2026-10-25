"""Write the locked (prospective) forecast of METR's TH1.1 frontier time horizon, issued 2026-10-25.

    python lock_forecast.py           # writes forecasts/FC-METR-TH11-LOCK-2026-10-25.json (refuses to overwrite)
    python lock_forecast.py --check   # recompute and confirm the committed file and its sha256

The forecast file is committed once and never regenerated. Its sha256 is in forecasts/SHA256SUMS and the
commit that added it is registered as lock_commit in evidence/protocol.yaml. Resolution rules are inside the
file. Unlike holdout.py, B-LOGLINEAR here reads the trend at the target date (lag 0): that choice was made
after the retrospective holdout showed the declared lag rule was broken, and before any outcome below exists.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

import holdout as H

HERE = pathlib.Path(__file__).resolve().parent
ISSUED = "2026-10-25"
CUTOFF = dt.date(2026, 10, 25)
TARGETS = [dt.date(2027, 4, 30), dt.date(2027, 10, 31)]
OUT = HERE / f"forecasts/FC-METR-TH11-LOCK-{ISSUED}.json"


def build() -> dict:
    rows = H.load_observations()
    info = H.info_set(rows, "TH1.1", CUTOFF)
    first = min(r["_avail"] for r in rows if r["suite"] == "TH1.1")
    fc = []
    for metric in ("p50_min", "p80_min"):
        for nosat in (False, True):
            for t in TARGETS:
                fc.append({
                    "metric": metric, "target_date": t.isoformat(),
                    "frontier_definition": "all published values" if not nosat else "values with p50 <= 960 min only",
                    "B-FLAT": H.b_flat(rows, "TH1.1", metric, CUTOFF, t, nosat, first),
                    "B-LOGLINEAR": H.b_loglinear(rows, "TH1.1", metric, CUTOFF, t, nosat, lag_zero=True),
                })
    return {
        "id": f"FC-METR-TH11-LOCK-{ISSUED}",
        "label": "locked",
        "issued": ISSUED,
        "information_cutoff": CUTOFF.isoformat(),
        "inputs": sorted({r["record_id"] for r in rows if r["suite"] == "TH1.1" and r["_avail"] <= CUTOFF}),
        "information_set_frontier": {m: H.frontier(info, m) for m in ("p50_min", "p80_min")},
        "units": "minutes of human expert time on METR's TH1.1 task suite (source-native)",
        "target": "F(T): the largest TH1.1 50% (80%) time horizon among values METR has published by date T",
        "forecasts": fc,
        "resolution": {
            "source": "metr.org/time-horizons and metr.org/assets/benchmark_results_1_1.yaml, or a METR release that labels its values TH1.1",
            "vintage": "values as public on the target date (first-published); a second score uses the latest vintage",
            "unresolved_if": [
                "METR publishes no new TH1.1 value for a model released after 2026-05-08 by the target date "
                "(the page has not been updated since 2026-09-08; an unchanged frontier is not evidence for B-FLAT)",
                "METR's new values use a different task suite or protocol (TH1.2, TH2, ...): not comparable without a declared mapping",
            ],
            "scoring": ["S-ABSLOGERR", "S-INTERVAL80 (natural-log scale)", "S-COVERAGE80"],
            "saturation": "METR calls values above 16 h (960 min) unreliable on this suite; both frontier definitions are scored and reported",
        },
        "not_claimed": "a forecast of AI capability, adoption or productivity in general: only of METR's TH1.1 measurements",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = json.dumps(build(), indent=1, sort_keys=True, default=str) + "\n"
    sums = HERE / "forecasts/SHA256SUMS"
    if a.check:
        committed = OUT.read_text()
        digest = hashlib.sha256(committed.encode()).hexdigest()
        if f"{digest}  {OUT.name}" not in sums.read_text():
            sys.exit(f"lock_forecast: {OUT.name} does not match forecasts/SHA256SUMS (a locked forecast was edited)")
        if committed != text:
            sys.exit("lock_forecast: the committed forecast no longer follows from data/observations.csv and the code")
        print(f"lock_forecast: {OUT.name} intact (sha256 {digest[:12]}...) and reproducible")
        return
    if OUT.exists():
        sys.exit(f"lock_forecast: {OUT} exists; a locked forecast is never overwritten")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text)
    with sums.open("a") as fh:
        fh.write(f"{hashlib.sha256(text.encode()).hexdigest()}  {OUT.name}\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
