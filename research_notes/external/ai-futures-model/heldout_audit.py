"""Which dated METR observations could serve as a held-out test of the AI Futures Model? (issue #45)

    python3 heldout_audit.py     # prints the audit table; tests/test_aifm.py checks its conclusions

Offline; reads only evidence/records.yaml and tools/evidence_tool.py. An observation is held out from AIFM only
if all three hold (evidence/protocol.yaml, P-CUTOFF and P-CONTAMINATION):
  1. it is independent of every AIFM output record (no shared depends_on ancestor, no common fitted_to dataset);
  2. it became available after AIFM's frozen information cutoff, the release commit date (no earlier public
     vintage of the code or inputs exists, so the cutoff cannot be placed earlier);
  3. it is on the suite AIFM's horizon is expressed in (TH1.1: its present_horizon is a TH1.1 p80); comparing
     with another suite needs a mapping that does not exist (#12, records' not_for).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
AIFM_OUTPUTS = ("EV-AIFM-REFERENCE-TRAJECTORY", "EV-AIFM-DANIEL-08-16-26")
AIFM_CUTOFF = "2026-09-09"  # commit 1c40ecdb, the only public commit (SOURCES.yaml)
AIFM_SUITE = "TH1.1"


def _evidence_tool():
    spec = importlib.util.spec_from_file_location("evidence_tool", ROOT / "tools/evidence_tool.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ET = _evidence_tool()


def audit() -> list[dict]:
    recs = ET.records_by_id()
    cutoff_last_day = ET.date_bounds(AIFM_CUTOFF)[1]
    rows = []
    for rid, r in sorted(recs.items()):
        if not rid.startswith("EV-METR-TH"):
            continue
        suite = "TH1.1" if rid.startswith("EV-METR-TH11") else "TH1.0"
        independent = all(ET.independent(recs, out, rid) for out in AIFM_OUTPUTS)
        after = ET.date_bounds(r["availability_date"])[0] > cutoff_last_day
        rows.append({"record": rid, "suite": suite, "available": r["availability_date"],
                     "independent_of_aifm_outputs": independent, "available_after_aifm_cutoff": after,
                     "on_aifm_suite": suite == AIFM_SUITE,
                     "held_out": independent and after and suite == AIFM_SUITE})
    return rows


def main() -> int:
    rows = audit()
    print("| record | suite | available | independent of AIFM outputs | after AIFM cutoff | on AIFM's suite | held out |")
    print("|---|---|---|---|---|---|---|")
    for x in rows:
        print(f"| {x['record']} | {x['suite']} | {x['available']} | {x['independent_of_aifm_outputs']} | "
              f"{x['available_after_aifm_cutoff']} | {x['on_aifm_suite']} | {x['held_out']} |")
    n = sum(x["held_out"] for x in rows)
    print(f"\n{n} of {len(rows)} METR time-horizon records are held out from AIFM (cutoff {AIFM_CUTOFF}).")
    if n == 0:
        print("No held-out test is possible yet (#45 stopping rule).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
