import pytest
from pydantic import ValidationError

from tests.conftest import random_expr
from ttl_designer.logic.build import build_netlist
from ttl_designer.logic.parser import parse_equations
from ttl_designer.models.catalog import load_catalog
from ttl_designer.models.netlist import CONST0, CONST1, GateKind, Output
from ttl_designer.models.physical import TieReason, TieTarget
from ttl_designer.sim.functional import check_equivalence
from ttl_designer.techmap.builder import NetBuilder
from ttl_designer.techmap.cells import CellLibrary, MapOptions
from ttl_designer.techmap.mapper import map_design
from ttl_designer.techmap.packing import absorb_spares, pack
from ttl_designer.techmap.strategies import STRATEGIES, MappingError, map_netlist

CATALOG = load_catalog()
LIB = CellLibrary(CATALOG, MapOptions())


def mapped(text: str, strategy: str, lib: CellLibrary = LIB):
    eqs = parse_equations(text)
    net = map_netlist(build_netlist(eqs), strategy, lib)
    return eqs, net


# --- NetBuilder -------------------------------------------------------------


def test_builder_cancels_double_negation_and_folds_constants():
    b = NetBuilder()
    na = b.not_("A")
    assert b.not_(na) == "A"
    assert b.gate(GateKind.AND, ["A", CONST1]) == "A"
    assert b.gate(GateKind.AND, ["A", CONST0]) == CONST0
    assert b.gate(GateKind.OR, ["A", CONST1]) == CONST1
    assert b.gate(GateKind.OR, ["A", "A"]) == "A"
    assert b.gate(GateKind.NAND, ["A", CONST1]) == na
    assert b.gate(GateKind.XOR, ["A", "A"]) == CONST0
    assert b.gate(GateKind.XOR, ["A", CONST1]) == na


def test_builder_hashes_commutative_gates_and_sweeps_dead_logic():
    b = NetBuilder()
    x = b.gate(GateKind.AND, ["A", "B"])
    assert b.gate(GateKind.AND, ["B", "A"]) == x
    b.gate(GateKind.OR, ["A", "C"])  # muerta: no llega a ninguna salida
    net = b.finish("t", ["A", "B", "C"], [Output(name="Y", net=x)])
    assert [g.kind for g in net.gates] == [GateKind.AND]


def test_internal_nets_never_collide_with_input_names():
    eqs = parse_equations("Y = n1 n2'")
    assert not check_equivalence(build_netlist(eqs), eqs)


# --- estrategias ------------------------------------------------------------


ALLOWED = {
    "nand": {GateKind.NAND},
    "nor": {GateKind.NOR},
    "nand+xor": {GateKind.NAND, GateKind.XOR},
    "nor+xor": {GateKind.NOR, GateKind.XOR},
    "mixta": {GateKind.AND, GateKind.OR, GateKind.NOT, GateKind.XOR, GateKind.NAND, GateKind.NOR},
}


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_strategies_are_equivalent_and_use_only_existing_cells(strategy, rng):
    vs = ["A", "B", "C", "D", "E"]
    for _ in range(60):
        eqs = [("Y", random_expr(rng, vs)), ("Z", random_expr(rng, vs))]
        net = map_netlist(build_netlist(eqs), strategy, LIB)
        assert not check_equivalence(net, eqs)
        for g in net.gates:
            assert g.kind in ALLOWED[strategy], (strategy, g)
            assert LIB.chip_for((g.kind, len(g.inputs))) is not None, g


def test_nand_inverter_ties_spare_input_high():
    _, net = mapped("Y = A'", "nand")
    (g,) = net.gates
    assert g.kind is GateKind.NAND and g.inputs == ["A", CONST1]


def test_nor_padding_uses_ground():
    _, net = mapped("Y = A'", "nor")
    (g,) = net.gates
    assert g.kind is GateKind.NOR and g.inputs == ["A", CONST0]


def test_five_input_and_pads_to_eight_input_nand():
    _, net = mapped("Y = A B C D E", "nand")
    kinds = sorted((g.kind, len(g.inputs)) for g in net.gates)
    assert (GateKind.NAND, 8) in kinds
    nand8 = next(g for g in net.gates if len(g.inputs) == 8)
    assert nand8.inputs.count(CONST1) == 3


def test_mixed_fuses_inverted_and_into_nand():
    _, net = mapped("Y = (A B)'", "mixta")
    assert [(g.kind, len(g.inputs)) for g in net.gates] == [(GateKind.NAND, 2)]


def test_strategy_without_cells_is_reported():
    lib = CellLibrary(CATALOG, MapOptions(excluded_parts=frozenset({"74LS02", "74LS27"})))
    with pytest.raises(MappingError):
        mapped("Y = A + B", "nor", lib)


# --- absorción y empaquetado ------------------------------------------------


def test_lonely_inverter_is_absorbed_into_spare_xor():
    eqs, net = mapped("Y = A ^ B; Z = C'", "mixta")
    assert {g.kind for g in net.gates} == {GateKind.XOR, GateKind.NOT}
    net2, moves = absorb_spares(net, LIB)
    assert len(moves) == 1 and moves[0].to_part == "74LS86"
    assert not check_equivalence(net2, eqs)
    design = pack(net2, LIB)
    assert design.parts() == {"74LS86": 1}
    xor_inv = next(g for g in net2.gates if CONST1 in g.inputs)
    assert xor_inv.inputs == ["C", CONST1]


def test_pack_uses_catalog_pins_and_ties_free_gates():
    eqs, net = mapped("Y = (A + B)'", "nor")
    design = pack(net, LIB)
    (chip,) = design.chips
    assert chip.part == "74LS02" and chip.vcc_pin == 14 and chip.gnd_pin == 7
    (p,) = design.placements
    assert (p.slot, p.input_pins, p.output_pin) == ("A", [2, 3], 1)
    free = [t for t in design.ties if t.reason is TieReason.FREE_GATE]
    assert len(free) == 6 and all(t.to is TieTarget.GND for t in free)
    out = net.outputs[0].net
    assert design.connections() == {"A": ["U1.2"], "B": ["U1.3"], out: ["U1.1"]}


def test_fixed_input_becomes_pullup_tie():
    _, net = mapped("Y = A'", "nand")
    design = pack(net, LIB)
    fixed = [t for t in design.ties if t.reason is TieReason.FIXED_INPUT]
    assert [(t.pin, t.to) for t in fixed] == [(2, TieTarget.PULLUP)]
    assert "$1" not in design.connections()


def test_physical_design_rejects_double_booked_slot():
    _, net = mapped("Y = (A B)' ; Z = (C D)'", "nand")
    design = pack(net, LIB)
    bad = design.model_dump()
    bad["placements"][1]["slot"] = bad["placements"][0]["slot"]
    with pytest.raises(ValidationError, match="mismo lugar"):
        type(design).model_validate(bad)


def test_refs_are_ordered_by_part_number():
    report = map_design(parse_equations("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)"), CATALOG)
    chips = report.selected.design.chips
    assert [(c.ref, c.part) for c in chips] == [("U1", "74LS00"), ("U2", "74LS86")]


# --- opciones y orquestador -------------------------------------------------


def test_open_collector_and_schmitt_excluded_by_default():
    parts = {
        c.part
        for c in CATALOG.chips
        if LIB.chip_for((GateKind(c.function.value), c.inputs_per_gate)) is c
    }
    assert not parts & {"74LS03", "74LS05", "74LS266", "74LS14", "74LS132"}


def test_open_collector_output_gets_pullup_when_allowed():
    lib = CellLibrary(CATALOG, MapOptions(allow_open_collector=True))
    _, net = mapped("Y = (A ^ B)'", "mixta", lib)
    design = pack(net, lib)
    assert design.parts() == {"74LS266": 1}
    assert any(t.reason is TieReason.OPEN_COLLECTOR for t in design.ties)


def test_excluding_xor_chip_falls_back_to_nand():
    opts = MapOptions(excluded_parts=frozenset({"74LS86"}))
    report = map_design(parse_equations("P = A ^ B"), CATALOG, options=opts)
    assert "74LS86" not in report.selected.design.parts()
    assert report.selected.design.parts() == {"74LS00": 1}


def test_every_candidate_is_equivalent_on_random_specs(rng):
    vs = ["A", "B", "C", "D"]
    for _ in range(25):
        eqs = [("Y", random_expr(rng, vs)), ("Z", random_expr(rng, vs))]
        report = map_design(eqs, CATALOG)
        assert all(c.equivalent for c in report.candidates if c.design), eqs
        assert report.selected is not None


def test_dont_cares_are_respected_by_mapping():
    report = map_design(parse_equations("Y = A B C + A' B' C'"), CATALOG, {"Y": [1, 3]})
    assert report.selected is not None and report.selected.equivalent


def test_warnings_flag_unverified_catalog_fields():
    report = map_design(parse_equations("P = A ^ B ^ C ^ D"), CATALOG)
    assert report.selected.design.parts() == {"74LS86": 1}
    assert any(w.startswith("74LS86:") for w in report.warnings)
