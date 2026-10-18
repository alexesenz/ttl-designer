import copy
import json

import pytest
from pydantic import ValidationError

from ttl_designer.models.catalog import Catalog, load_catalog

# Pinout estándar del 74LS00; valores eléctricos en null a propósito: este
# fixture prueba el esquema, no es una fuente de datos.
CHIP_74LS00 = {
    "part": "74LS00",
    "description": "Quad 2-input NAND",
    "function": "NAND",
    "inputs_per_gate": 2,
    "gates_per_package": 4,
    "output_type": "totem_pole",
    "package_pins": 14,
    "power_pins": {"vcc": 14, "gnd": 7},
    "gates": [
        {"id": "A", "inputs": [1, 2], "output": 3},
        {"id": "B", "inputs": [4, 5], "output": 6},
        {"id": "C", "inputs": [9, 10], "output": 8},
        {"id": "D", "inputs": [12, 13], "output": 11},
    ],
    "timing": {"tplh_typ_ns": None, "tplh_max_ns": None},
    "sources": ["s1"],
}

CATALOG = {
    "schema_version": "1.0",
    "family": "74LS",
    "family_defaults": {"sources": ["s1"]},
    "chips": [CHIP_74LS00],
    "source_index": {"s1": {"title": "fixture", "url": "https://example.invalid"}},
}


def mutated(fn):
    data = copy.deepcopy(CATALOG)
    fn(data["chips"][0], data)
    return data


def test_valid_catalog_loads(tmp_path):
    p = tmp_path / "cat.json"
    p.write_text(json.dumps(CATALOG))
    cat = load_catalog(p)
    assert cat.chip("74LS00").gates[2].output == 8


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda c, d: c["gates"].pop(), "compuertas"),
        (lambda c, d: c["gates"][0]["inputs"].append(5), "entradas"),
        (lambda c, d: c["gates"][1].update(output=3), "repetidos"),
        (lambda c, d: c["gates"][3].update(output=15), "pinout incompleto"),
        (lambda c, d: c.update(timing={"tphl_typ_ns": 20, "tphl_max_ns": 10}), "típico"),
        (lambda c, d: c.update(unknown_field=1), "extra"),
        (lambda c, d: c.update(sources=["nope"]), "source_index"),
        (lambda c, d: d["chips"].append(copy.deepcopy(c)), "repetidos"),
    ],
)
def test_invalid_catalogs(mutation, message):
    with pytest.raises(ValidationError, match=message):
        Catalog.model_validate(mutated(mutation))


def test_nc_pins_complete_pinout():
    def to_dual_4(c, d):
        c.update(
            part="74LS20",
            function="NAND",
            inputs_per_gate=4,
            gates_per_package=2,
            nc_pins=[3, 11],
            gates=[
                {"id": "A", "inputs": [1, 2, 4, 5], "output": 6},
                {"id": "B", "inputs": [9, 10, 12, 13], "output": 8},
            ],
        )

    Catalog.model_validate(mutated(to_dual_4))
