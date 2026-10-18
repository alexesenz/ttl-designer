"""Simulación funcional sin retardos sobre el netlist lógico.

Evalúa todas las filas de la tabla de verdad en una sola pasada usando
vectores bit-paralelos (un entero por red).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import and_, or_, xor

from ..logic.ast import Expr
from ..logic.truthtable import TruthTable, input_vectors, ones
from ..models.netlist import CONST0, CONST1, GateKind, Netlist


def _eval_gate(kind: GateKind, values: list[int], mask: int) -> int:
    if kind is GateKind.BUF:
        return values[0]
    if kind is GateKind.NOT:
        return ~values[0] & mask
    if kind in (GateKind.AND, GateKind.NAND):
        v = reduce(and_, values, mask)
    elif kind in (GateKind.OR, GateKind.NOR):
        v = reduce(or_, values, 0)
    else:
        v = reduce(xor, values, 0)
    if kind in (GateKind.NAND, GateKind.NOR, GateKind.XNOR):
        v = ~v & mask
    return v


def simulate_vectors(netlist: Netlist, env: dict[str, int], mask: int) -> dict[str, int]:
    """Valor de cada red como vector bit-paralelo."""
    nets = {CONST0: 0, CONST1: mask}
    for name in netlist.inputs:
        nets[name] = env[name] & mask
    for g in netlist.topological_order():
        nets[g.output] = _eval_gate(g.kind, [nets[n] for n in g.inputs], mask)
    return nets


def simulate(netlist: Netlist, inputs: dict[str, bool | int]) -> dict[str, int]:
    """Evalúa un único vector de entrada; devuelve el valor de cada salida."""
    missing = set(netlist.inputs) - set(inputs)
    if missing:
        raise ValueError(f"faltan entradas: {', '.join(sorted(missing))}")
    nets = simulate_vectors(netlist, {k: int(bool(v)) for k, v in inputs.items()}, 1)
    return {o.name: nets[o.net] for o in netlist.outputs}


def netlist_truth_table(netlist: Netlist, inputs: list[str] | None = None) -> TruthTable:
    inputs = inputs if inputs is not None else list(netlist.inputs)
    vectors, mask = input_vectors(len(inputs))
    env = dict(zip(inputs, vectors, strict=True))
    for name in netlist.inputs:
        env.setdefault(name, 0)
    nets = simulate_vectors(netlist, env, mask)
    columns = {o.name: nets[o.net] for o in netlist.outputs}
    return TruthTable(inputs, [o.name for o in netlist.outputs], columns)


@dataclass
class Mismatch:
    output: str
    row: int
    inputs: dict[str, int]
    expected: int
    actual: int


def check_equivalence(
    netlist: Netlist,
    equations: list[tuple[str, Expr]],
    dont_cares: dict[str, list[int]] | None = None,
    max_reports: int = 10,
) -> list[Mismatch]:
    """Compara el netlist contra la especificación en todas las filas.

    Las filas en ``dont_cares[salida]`` se ignoran. Devuelve hasta
    ``max_reports`` contraejemplos; lista vacía = equivalentes.
    """
    dont_cares = dont_cares or {}
    inputs = sorted(set(netlist.inputs) | {v for _, e in equations for v in e.variables()})
    vectors, mask = input_vectors(len(inputs))
    env = dict(zip(inputs, vectors, strict=True))
    nets = simulate_vectors(netlist, env, mask)
    outputs = {o.name: o.net for o in netlist.outputs}
    n = len(inputs)

    mismatches: list[Mismatch] = []
    for name, expr in equations:
        if name not in outputs:
            raise ValueError(f"el netlist no tiene la salida {name!r}")
        expected = expr.eval(env, mask)
        actual = nets[outputs[name]]
        care = mask
        for row in dont_cares.get(name, []):
            care &= ~(1 << row)
        for row in ones((expected ^ actual) & care):
            mismatches.append(
                Mismatch(
                    output=name,
                    row=row,
                    inputs={v: (row >> (n - 1 - i)) & 1 for i, v in enumerate(inputs)},
                    expected=(expected >> row) & 1,
                    actual=(actual >> row) & 1,
                )
            )
            if len(mismatches) >= max_reports:
                return mismatches
    return mismatches
