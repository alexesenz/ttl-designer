"""Construcción de un netlist lógico a partir de ecuaciones.

Aplica hashing estructural: subexpresiones idénticas (módulo orden de los
operandos en operadores conmutativos) se instancian una sola vez.
"""

from __future__ import annotations

from ..models.netlist import CONST0, CONST1, Gate, GateKind, Netlist, Output
from .ast import And, Const, Expr, NAry, Not, Or, Var, Xor
from .truthtable import collect_inputs

# Prefijo de redes internas: "~" no puede aparecer en un identificador del parser,
# así que una red interna nunca choca con el nombre de una entrada.
INTERNAL_NET_PREFIX = "~n"

_KIND = {And: GateKind.AND, Or: GateKind.OR, Xor: GateKind.XOR}


class _Builder:
    def __init__(self) -> None:
        self.gates: list[Gate] = []
        self.cache: dict[tuple[GateKind, tuple[str, ...]], str] = {}

    def net(self, e: Expr) -> str:
        if isinstance(e, Var):
            return e.name
        if isinstance(e, Const):
            return CONST1 if e.value else CONST0
        if isinstance(e, Not):
            return self.gate(GateKind.NOT, [self.net(e.arg)])
        assert isinstance(e, NAry)
        kind = _KIND[type(e)]
        return self.gate(kind, [self.net(a) for a in e.args])

    def gate(self, kind: GateKind, inputs: list[str]) -> str:
        key = (kind, tuple(inputs) if kind.unary else tuple(sorted(inputs)))
        if key in self.cache:
            return self.cache[key]
        n = len(self.gates) + 1
        out = f"{INTERNAL_NET_PREFIX}{n}"
        self.gates.append(Gate(id=f"G{n}", kind=kind, inputs=inputs, output=out))
        self.cache[key] = out
        return out


def build_netlist(
    equations: list[tuple[str, Expr]], name: str = "circuit", inputs: list[str] | None = None
) -> Netlist:
    """``inputs`` permite conservar entradas que la minimización eliminó de las ecuaciones."""
    used = collect_inputs(equations)
    if inputs is None:
        inputs = used
    elif missing := sorted(set(used) - set(inputs)):
        raise ValueError(f"variables no declaradas como entradas: {missing}")
    b = _Builder()
    outputs = [Output(name=o, net=b.net(e)) for o, e in equations]
    return Netlist(name=name, inputs=inputs, outputs=outputs, gates=b.gates)
