"""Mapeo tecnológico: netlist lógico → netlist de celdas disponibles (§MAPEO).

Tres fases por estrategia:

A. Descomposición: compuertas AND/OR/XOR de fan-in acotado más NOT, con
   NAND/NOR/XNOR expresadas como NOT de su base.
B. Traducción a las primitivas de la estrategia (mixta, solo NAND, solo NOR, o
   NAND/NOR conservando las XOR como celda 7486), con cancelación de dobles
   negaciones.
C. Ajuste a celdas: el NOT se baja a la celda que corresponda y cada compuerta
   se lleva al menor número de entradas disponible, rellenando con el valor
   neutro (§MAPEO: entradas sobrantes a pull-up o a GND).
"""

from __future__ import annotations

from collections.abc import Callable
from math import ceil

from ..models.netlist import CONST1, Gate, GateKind, Netlist
from .builder import NetBuilder, fanout
from .cells import NEUTRAL, CellLibrary

STRATEGIES = ("mixta", "nand", "nor", "nand+xor", "nor+xor")


class MappingError(ValueError):
    """La estrategia no puede realizarse con las celdas disponibles."""


def map_netlist(netlist: Netlist, strategy: str, lib: CellLibrary) -> Netlist:
    if strategy not in STRATEGIES:
        raise ValueError(f"estrategia desconocida: {strategy!r}")
    limits = _phase_a_limits(strategy, lib)
    a = _decompose(netlist, limits)
    b = _translate(a, strategy, lib)
    return _fit_cells(b, strategy, lib)


# --- fase A ----------------------------------------------------------------


def _phase_a_limits(strategy: str, lib: CellLibrary) -> dict[GateKind, int]:
    if strategy.startswith("nand"):
        m = lib.max_arity(GateKind.NAND)
        limits = {GateKind.AND: m, GateKind.OR: m, GateKind.XOR: 2}
    elif strategy.startswith("nor"):
        m = lib.max_arity(GateKind.NOR)
        limits = {GateKind.AND: m, GateKind.OR: m, GateKind.XOR: 2}
    else:
        limits = {
            GateKind.AND: max(lib.max_arity(GateKind.AND), lib.max_arity(GateKind.NAND)),
            GateKind.OR: max(lib.max_arity(GateKind.OR), lib.max_arity(GateKind.NOR)),
            GateKind.XOR: 2,
        }
    missing = [k for k, m in limits.items() if m < 2 and k is not GateKind.XOR]
    if missing:
        raise MappingError(f"sin celdas para la estrategia {strategy}: {missing}")
    return limits


def _decompose(netlist: Netlist, limits: dict[GateKind, int]) -> Netlist:
    b = NetBuilder()
    net: dict[str, str] = {}

    def src(x: str) -> str:
        return net.get(x, x)

    def tree(kind: GateKind, ins: list[str]) -> str:
        m = limits[kind]
        if len(ins) <= m:
            return b.gate(kind, ins)
        k = ceil(len(ins) / m)
        size = ceil(len(ins) / k)
        children = [tree(kind, ins[i : i + size]) for i in range(0, len(ins), size)]
        return tree(kind, children)

    base = {GateKind.NAND: GateKind.AND, GateKind.NOR: GateKind.OR, GateKind.XNOR: GateKind.XOR}
    for g in netlist.topological_order():
        ins = [src(x) for x in g.inputs]
        if g.kind is GateKind.BUF:
            out = ins[0]
        elif g.kind is GateKind.NOT:
            out = b.not_(ins[0])
        elif g.kind in base:
            out = b.not_(tree(base[g.kind], ins))
        else:
            out = tree(g.kind, ins)
        net[g.output] = out
    outputs = [o.model_copy(update={"net": src(o.net)}) for o in netlist.outputs]
    return b.finish(netlist.name, netlist.inputs, outputs)


# --- fase B ----------------------------------------------------------------


def _translate(a: Netlist, strategy: str, lib: CellLibrary) -> Netlist:
    b = NetBuilder()
    net: dict[str, str] = {}
    drivers = {g.output: g for g in a.gates}
    fo = fanout(a)

    def src(x: str) -> str:
        return net.get(x, x)

    rules: dict[str, Callable[[Gate, list[str]], str]] = {
        "mixta": lambda g, ins: _mixed(b, g, ins, drivers, fo, src, lib),
        "nand": lambda g, ins: _nand(b, g, ins, keep_xor=False),
        "nor": lambda g, ins: _nor(b, g, ins, keep_xor=False),
        "nand+xor": lambda g, ins: _nand(b, g, ins, keep_xor=lib.has(GateKind.XOR, 2)),
        "nor+xor": lambda g, ins: _nor(b, g, ins, keep_xor=lib.has(GateKind.XOR, 2)),
    }
    rule = rules[strategy]
    for g in a.topological_order():
        net[g.output] = rule(g, [src(x) for x in g.inputs])
    outputs = [o.model_copy(update={"net": src(o.net)}) for o in a.outputs]
    return b.finish(a.name, a.inputs, outputs)


def _mixed(
    b: NetBuilder,
    g: Gate,
    ins: list[str],
    drivers: dict[str, Gate],
    fo: dict[str, int],
    src: Callable[[str], str],
    lib: CellLibrary,
) -> str:
    if g.kind is GateKind.NOT:
        # NOT(AND) → NAND, NOT(OR) → NOR, NOT(XOR) → XNOR cuando la compuerta interna
        # no se usa en otro lado y la celda fusionada existe.
        d = drivers.get(g.inputs[0])
        fused = {
            GateKind.AND: GateKind.NAND,
            GateKind.OR: GateKind.NOR,
            GateKind.XOR: GateKind.XNOR,
        }
        if d is not None and d.kind in fused and fo[d.output] == 1:
            kind = fused[d.kind]
            if lib.fit(kind, len(d.inputs)) is not None:
                return b.gate(kind, [src(x) for x in d.inputs])
        return b.not_(ins[0])
    if g.kind is GateKind.XOR and not lib.has(GateKind.XOR, 2):
        return _xor_nand(b, ins[0], ins[1])
    for kind, alt in ((GateKind.AND, GateKind.NAND), (GateKind.OR, GateKind.NOR)):
        if g.kind is kind and lib.fit(kind, len(ins)) is None:
            return b.not_(b.gate(alt, ins))
    return b.gate(g.kind, ins)


def _xor_nand(b: NetBuilder, x: str, y: str) -> str:
    n1 = b.gate(GateKind.NAND, [x, y])
    return b.gate(GateKind.NAND, [b.gate(GateKind.NAND, [x, n1]), b.gate(GateKind.NAND, [y, n1])])


def _nand(b: NetBuilder, g: Gate, ins: list[str], keep_xor: bool) -> str:
    if g.kind is GateKind.NOT:
        return b.not_(ins[0])
    if g.kind is GateKind.AND:
        return b.not_(b.gate(GateKind.NAND, ins))
    if g.kind is GateKind.OR:
        return b.gate(GateKind.NAND, [b.not_(x) for x in ins])
    assert g.kind is GateKind.XOR
    if keep_xor:
        return b.gate(GateKind.XOR, ins)
    return _xor_nand(b, ins[0], ins[1])


def _nor(b: NetBuilder, g: Gate, ins: list[str], keep_xor: bool) -> str:
    if g.kind is GateKind.NOT:
        return b.not_(ins[0])
    if g.kind is GateKind.OR:
        return b.not_(b.gate(GateKind.NOR, ins))
    if g.kind is GateKind.AND:
        return b.gate(GateKind.NOR, [b.not_(x) for x in ins])
    assert g.kind is GateKind.XOR
    if keep_xor:
        return b.gate(GateKind.XOR, ins)
    x, y = ins
    n1 = b.gate(GateKind.NOR, [x, y])
    xnor = b.gate(GateKind.NOR, [b.gate(GateKind.NOR, [x, n1]), b.gate(GateKind.NOR, [y, n1])])
    return b.not_(xnor)


# --- fase C ----------------------------------------------------------------


def _fit_cells(netlist: Netlist, strategy: str, lib: CellLibrary) -> Netlist:
    gates: list[Gate] = []
    for g in netlist.gates:
        kind, ins = g.kind, list(g.inputs)
        if kind is GateKind.NOT:
            kind, ins = _lower_not(strategy, lib, ins[0])
        size = lib.fit(kind, len(ins))
        if size is None:
            raise MappingError(f"{g.id}: no hay celda {kind} de {len(ins)} entradas")
        if not kind.unary:
            ins += [NEUTRAL[kind]] * (size - len(ins))
        gates.append(Gate(id=g.id, kind=kind, inputs=ins, output=g.output))
    return Netlist(name=netlist.name, inputs=netlist.inputs, outputs=netlist.outputs, gates=gates)


def _lower_not(strategy: str, lib: CellLibrary, x: str) -> tuple[GateKind, list[str]]:
    """Inversor según la estrategia; la entrada sobrante va al valor neutro (§MAPEO)."""
    if strategy == "mixta" and lib.has(GateKind.NOT, 1):
        return GateKind.NOT, [x]
    if not strategy.startswith("nor") and lib.max_arity(GateKind.NAND) >= 2:
        return GateKind.NAND, [x, CONST1]
    if lib.max_arity(GateKind.NOR) >= 2:
        return GateKind.NOR, [x, NEUTRAL[GateKind.NOR]]
    raise MappingError("no hay celda para implementar un inversor")
