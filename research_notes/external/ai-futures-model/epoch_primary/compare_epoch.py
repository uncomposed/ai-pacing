#!/usr/bin/env python3
"""Compare AIFM's bundled Epoch CSVs (pinned upstream checkout) with the primary Epoch files in this folder (#66).

Offline. Needs `../fetch_upstream.sh` to have run. Writes compare_epoch.json. Differences are reported, never
reconciled: neither side is edited. The ECI file AIFM bundles (per model version, 815 rows) is no longer in Epoch's
benchmark_data.zip, which now ships epoch_capabilities_index/eci_scores.csv (per model), so ECI is compared per
model name where the release date also matches.
"""
import csv, hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLED = HERE.parent / ".upstream" / "inputs" / "epoch"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def frontier(rows):
    best, out = None, []
    for d, s in sorted(rows):
        if best is None or s > best:
            best = s
            out.append([d, s])
    return out


def eci():
    b = [r for r in csv.DictReader(open(BUNDLED / "epoch_capabilities_index.csv", encoding="utf-8")) if r["ECI Score"]]
    n = {r["Model"]: r for r in csv.DictReader(open(HERE / "eci_scores.csv", encoding="utf-8"))}
    diffs, names = [], {r["Model name"] for r in b}
    for r in b:
        k = r["Model name"]
        if k in n and n[k]["date"] == r["Release date"]:
            diffs.append(float(r["ECI Score"]) - float(n[k]["eci"]))
    return {
        "bundled_scored_rows": len(b), "bundled_model_names": len(names), "primary_models": len(n),
        "bundled_names_absent_from_primary": sorted(names - set(n)),
        "primary_names_absent_from_bundled": len(set(n) - names),
        "paired_rows_same_name_and_date": len(diffs),
        "rows_with_identical_score": sum(1 for d in diffs if abs(d) < 0.005),
        "diff_bundled_minus_primary": {"mean": round(sum(diffs) / len(diffs), 3), "min": round(min(diffs), 2), "max": round(max(diffs), 2)},
        "latest_release_bundled": max(r["Release date"] for r in b), "latest_release_primary": max(r["date"] for r in n.values()),
        "frontier_tail_bundled": frontier([(r["Release date"], float(r["ECI Score"])) for r in b])[-3:],
        "frontier_tail_primary": frontier([(r["date"], float(r["eci"])) for r in n.values()])[-3:],
    }


def revenue(company, fname):
    cur = []
    for row in csv.DictReader(open(HERE / "ai_companies_revenue_reports.csv", encoding="utf-8")):
        v = (row["Annualized revenue (USD)"] or "").strip()
        if row["Company"] != company or row["Scope"] != "Full company" or not v:
            continue  # the filter AIFM's scripts/bridge/epoch_revenue_to_ts.py applies
        cur.append((row["Date"].strip(), "%.0f" % float(v), row["Annualized revenue type"].strip(), row["Confidence"].strip(),
                    row["Source type"].strip(), row["Source 1"].strip(), row["Report date"].strip()))
    bund = [(r["date"], r["annualized_revenue_usd"], r["revenue_type"], r["confidence"], r["source_type"], r["source_url"], r["report_date"])
            for r in csv.DictReader(open(BUNDLED / fname, encoding="utf-8"))]
    return {"bundled_rows": len(bund), "primary_rows_after_AIFM_filter": len(cur), "identical": sorted(bund) == sorted(cur),
            "only_in_bundled": [list(x) for x in sorted(set(bund) - set(cur))],
            "only_in_primary": [list(x) for x in sorted(set(cur) - set(bund))]}


def main():
    if not BUNDLED.exists():
        sys.exit("run ../fetch_upstream.sh first")
    out = {
        "primary_sha256": {f: sha(HERE / f) for f in ("eci_scores.csv", "ai_companies_revenue_reports.csv")},
        "bundled_sha256": {f.name: sha(f) for f in sorted(BUNDLED.glob("*.csv"))},
        "eci": eci(),
        "revenue_anthropic": revenue("Anthropic", "epoch_anthropic_revenue.csv"),
        "revenue_openai": revenue("OpenAI", "epoch_openai_revenue.csv"),
    }
    (HERE / "compare_epoch.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))


main()
