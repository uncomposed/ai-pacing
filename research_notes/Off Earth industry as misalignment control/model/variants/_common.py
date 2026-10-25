"""Shared helpers for the issue #9 variants. Nothing here changes equilibrium_model.py, robust_design.py or ci_sims.py:
the variants import the baseline model read-only and keep the full solver as the explicit baseline."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)
OUT = os.path.join(MODEL, "results", "variants")
if MODEL not in sys.path:
    sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")


def save_json(name: str, obj) -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".json")
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=True, default=_default)
        f.write("\n")
    return path


def _default(x):
    try:
        return float(x)
    except Exception:
        return str(x)


def md_table(rows, header) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fmt(x, nd=3):
    if x is None:
        return "none"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, (int,)):
        return str(x)
    return f"{x:.{nd}g}"
