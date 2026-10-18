"""Constructor incremental de netlists con simplificación local.

Aplica plegado de constantes, idempotencia, cancelación de dobles negaciones y
hashing estructural al crear cada compuerta; al terminar elimina las compuertas
que no alimentan ninguna salida.
"""

from __future__ import annotations

from collections import Counter

from ..logic.build import INTERNAL_NET_PREFIX
from ..models.netlist import CONST0, CONST1, CONSTANT_NETS, Gate, GateKind, Netlist, Output

_ASSOC = {
    GateKind.AND: (CONST0, CONST1),  # (absorbente, neutro)
    GateKind.OR: (CONST1, CONST0),
}
_NEGATED = {GateKind.NAND: GateKind.AND, GateKind.NOR: GateKind.OR, GateKind.XNOR: GateKind.XOR}


class NetBuilder:
    def __init__(self) -> None:
        self.gates: list[Gate] = []
        self.driver: dict[str, Gate] = {}
        self._cache: dict[tuple[GateKind, tuple[str, ...]], str] = {}

    # --- operaciones lógicas ---------------------------------------------

    def not_(self, x: str) -> str:
        if x == CONST0:
            return CONST1
        if x == CONST1:
            return CONST0
        g = self.driver.get(x)
        if g is not None and g.kind is GateKind.NOT:
            return g.inputs[0]
        return self._emit(GateKind.NOT, [x])

    def gate(self, kind: GateKind, inputs: list[str]) -> str:
        if kind is GateKind.NOT:
            return self.not_(inputs[0])
        if kind is GateKind.BUF:
            return inputs[0]
        if kind in _NEGATED:
            base = _NEGATED[kind]
            folded = self._fold(base, inputs)
            if isinstance(folded, str):
                return self.not_(folded)
            return self._emit(kind, folded)
        folded = self._fold(kind, inputs)
        if isinstance(folded, str):
            return folded
        return self._emit(kind, folded)

    def _fold(self, kind: GateKind, inputs: list[str]) -> str | list[str]:
        """Devuelve una red si la función se reduce, o la lista de entradas restante."""
        if kind in _ASSOC:
            absorbing, neutral = _ASSOC[kind]
            if absorbing in inputs:
                return absorbing
            ins = list(dict.fromkeys(i for i in inputs if i != neutral))
            if not ins:
                return neutral
            if len(ins) == 1:
                return ins[0]
            return ins
        assert kind is GateKind.XOR
        parity = inputs.count(CONST1) % 2
        counts = Counter(i for i in inputs if i not in CONSTANT_NETS)
        ins = [i for i, c in counts.items() if c % 2]
        if not ins:
            return CONST1 if parity else CONST0
        if len(ins) == 1:
            return self.not_(ins[0]) if parity else ins[0]
        if parity:
            return self.not_(self._emit(GateKind.XOR, ins))
        return ins

    def _emit(self, kind: GateKind, inputs: list[str]) -> str:
        key = (kind, tuple(inputs) if kind.unary else tuple(sorted(inputs)))
        if key in self._cache:
            return self._cache[key]
        n = len(self.gates) + 1
        out = f"{INTERNAL_NET_PREFIX}{n}"
        g = Gate(id=f"G{n}", kind=kind, inputs=inputs, output=out)
        self.gates.append(g)
        self.driver[out] = g
        self._cache[key] = out
        return out

    # --- cierre ------------------------------------------------------------

    def finish(self, name: str, inputs: list[str], outputs: list[Output]) -> Netlist:
        """Elimina compuertas muertas y renumera en orden de creación."""
        live: set[str] = set()
        stack = [o.net for o in outputs]
        while stack:
            net = stack.pop()
            g = self.driver.get(net)
            if g is None or g.id in live:
                continue
            live.add(g.id)
            stack.extend(g.inputs)
        kept = [g for g in self.gates if g.id in live]
        rename = {g.output: f"{INTERNAL_NET_PREFIX}{i}" for i, g in enumerate(kept, 1)}
        gates = [
            Gate(
                id=f"G{i}",
                kind=g.kind,
                inputs=[rename.get(x, x) for x in g.inputs],
                output=rename[g.output],
            )
            for i, g in enumerate(kept, 1)
        ]
        outs = [Output(name=o.name, net=rename.get(o.net, o.net)) for o in outputs]
        return Netlist(name=name, inputs=inputs, outputs=outs, gates=gates)


def fanout(netlist: Netlist) -> Counter[str]:
    """Número de consumidores de cada red (entradas de compuerta y salidas)."""
    c: Counter[str] = Counter()
    for g in netlist.gates:
        c.update(g.inputs)
    c.update(o.net for o in netlist.outputs)
    return c
