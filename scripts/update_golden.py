"""Regenera tests/golden/mapping_baseline.json. Exige una razón, que queda en _meta.

Uso:  python scripts/update_golden.py --reason "por qué cambia el mapeo"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tests.golden.circuits import CIRCUITS, summarize  # noqa: E402
from ttl_designer.logic.parser import parse_equations  # noqa: E402
from ttl_designer.models.catalog import load_catalog  # noqa: E402
from ttl_designer.techmap.mapper import map_design  # noqa: E402

BASELINE = REPO / "tests" / "golden" / "mapping_baseline.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reason", required=True, help="motivo del cambio de baseline")
    args = ap.parse_args()

    catalog = load_catalog()
    circuits = {
        name: summarize(map_design(parse_equations(text), catalog, dcs))
        for name, (text, dcs) in CIRCUITS.items()
    }
    old = json.loads(BASELINE.read_text(encoding="utf-8"))["circuits"] if BASELINE.exists() else {}
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    data = {
        "_meta": {
            "reason": args.reason,
            "date": dt.date.today().isoformat(),
            "base_commit": commit or "unknown",
        },
        "circuits": circuits,
    }
    BASELINE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for name, new in circuits.items():
        if old.get(name) != new:
            print(f"{name}: {old.get(name)} -> {new}")
    print(f"escrito {BASELINE.relative_to(REPO)}")


if __name__ == "__main__":
    main()
