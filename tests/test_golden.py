"""Circuitos dorados (§MAPEO): el mapeo de cada uno está fijado en el baseline.

Si un cambio mueve un resultado a propósito, regenera con
``python scripts/update_golden.py --reason "..."`` y explica el cambio en el commit.
"""

import json
from pathlib import Path

import pytest

from tests.golden.circuits import CIRCUITS, summarize
from ttl_designer.logic.parser import parse_equations
from ttl_designer.models.catalog import load_catalog
from ttl_designer.techmap.mapper import map_design

BASELINE = json.loads(
    (Path(__file__).parent / "golden" / "mapping_baseline.json").read_text(encoding="utf-8")
)
CATALOG = load_catalog()


def test_baseline_has_reason_and_covers_all_circuits():
    assert BASELINE["_meta"]["reason"].strip()
    assert set(BASELINE["circuits"]) == set(CIRCUITS)


@pytest.mark.parametrize("name", sorted(CIRCUITS))
def test_golden_circuit(name):
    text, dcs = CIRCUITS[name]
    report = map_design(parse_equations(text), CATALOG, dcs)
    assert all(c.equivalent for c in report.candidates if c.design)
    assert summarize(report) == BASELINE["circuits"][name], (
        "el mapeo cambió; si es intencional: scripts/update_golden.py --reason '...'"
    )
