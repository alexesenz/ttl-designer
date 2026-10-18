import pytest
from pydantic import ValidationError

from tests.conftest import random_expr
from ttl_designer.logic.build import build_netlist
from ttl_designer.logic.parser import parse_equations
from ttl_designer.logic.qm import minimize
from ttl_designer.logic.truthtable import truth_table
from ttl_designer.models.netlist import Gate, GateKind, Netlist, Output
from ttl_designer.sim.functional import check_equivalence, netlist_truth_table, simulate


def g(id, kind, inputs, output):
    return Gate(id=id, kind=GateKind(kind), inputs=inputs, output=output)


def test_arity_validation():
    with pytest.raises(ValidationError):
        g("G1", "NOT", ["A", "B"], "n1")
    with pytest.raises(ValidationError):
        g("G1", "AND", ["A"], "n1")


def test_double_driver_rejected():
    with pytest.raises(ValidationError, match="manejada"):
        Netlist(
            inputs=["A", "B"],
            outputs=[Output(name="Y", net="n1")],
            gates=[g("G1", "NOT", ["A"], "n1"), g("G2", "NOT", ["B"], "n1")],
        )


def test_undriven_net_rejected():
    with pytest.raises(ValidationError, match="no tiene quien"):
        Netlist(
            inputs=["A"],
            outputs=[Output(name="Y", net="n1")],
            gates=[g("G1", "AND", ["A", "X"], "n1")],
        )


def test_combinational_loop_rejected():
    with pytest.raises(ValidationError, match="lazo"):
        Netlist(
            inputs=["A"],
            outputs=[Output(name="Y", net="n2")],
            gates=[g("G1", "NAND", ["A", "n2"], "n1"), g("G2", "NOT", ["n1"], "n2")],
        )


def test_nand_nand_xor_and_levels():
    gates = [
        g("G1", "NAND", ["A", "B"], "n1"),
        g("G2", "NAND", ["A", "n1"], "n2"),
        g("G3", "NAND", ["B", "n1"], "n3"),
        g("G4", "NAND", ["n2", "n3"], "Y"),
    ]
    nl = Netlist(inputs=["A", "B"], outputs=[Output(name="Y", net="Y")], gates=gates)
    assert nl.depth() == 3
    assert nl.levels() == {"G1": 1, "G2": 2, "G3": 2, "G4": 3}
    assert not check_equivalence(nl, parse_equations("Y = A ^ B"))
    assert simulate(nl, {"A": 1, "B": 0}) == {"Y": 1}


def test_all_gate_kinds():
    eqs = parse_equations("Y = A")
    for kind, fn in {
        "AND": lambda a, b: a & b,
        "OR": lambda a, b: a | b,
        "XOR": lambda a, b: a ^ b,
        "NAND": lambda a, b: 1 - (a & b),
        "NOR": lambda a, b: 1 - (a | b),
        "XNOR": lambda a, b: 1 - (a ^ b),
    }.items():
        nl = Netlist(
            inputs=["A", "B"],
            outputs=[Output(name="Y", net="n")],
            gates=[g("G", kind, ["A", "B"], "n")],
        )
        for a in (0, 1):
            for b in (0, 1):
                assert simulate(nl, {"A": a, "B": b})["Y"] == fn(a, b), kind
    del eqs


def test_structural_hashing_shares_subexpressions():
    nl = build_netlist(parse_equations("X = A B + C; Y = B A + D"))
    and_gates = [x for x in nl.gates if x.kind is GateKind.AND]
    assert len(and_gates) == 1


def test_constants_and_passthrough():
    nl = build_netlist(parse_equations("Y = A; Z = 1; W = A·0"))
    t = netlist_truth_table(nl)
    assert [row[1] for row in t.rows()] == [[0, 1, 0], [1, 1, 0]]


def test_mismatch_reported():
    nl = build_netlist(parse_equations("Y = A + B"))
    mism = check_equivalence(nl, parse_equations("Y = A B"))
    assert {m.row for m in mism} == {1, 2}
    assert check_equivalence(nl, parse_equations("Y = A B"), {"Y": [1, 2]}) == []


def test_random_pipeline_equivalence(rng):
    vs = ["A", "B", "C", "D", "E"]
    for _ in range(100):
        eqs = [("Y", random_expr(rng, vs)), ("Z", random_expr(rng, vs))]
        assert not check_equivalence(build_netlist(eqs), eqs)
        t = truth_table(eqs, vs)
        minimized = [(o, minimize(5, t.minterms(o)).to_expr(vs)) for o in t.outputs]
        assert not check_equivalence(build_netlist(minimized), eqs)
