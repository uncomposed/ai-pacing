"""Shared helpers for the docking scripts. Run every script from model/:  python3 docking/<name>.py
Nothing here changes equilibrium_model.py; each docked model is a parameter setting of the unchanged solver."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, MODEL)
os.environ.setdefault("OMP_NUM_THREADS", "1")


def save(name: str, obj) -> str:
    path = os.path.join(OUT, name + ".json")
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=float)
    return path


def md_table(rows, header) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)
