"""Netlist lógico: compuertas abstractas conectadas por redes con nombre.

Es independiente de la tecnología: las compuertas pueden tener cualquier
fan-in. El mapeo a chips 74LS y el empaquetado trabajan sobre este modelo.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

CONST0 = "$0"
CONST1 = "$1"
CONSTANT_NETS = (CONST0, CONST1)


class GateKind(StrEnum):
    BUF = "BUF"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    NAND = "NAND"
    NOR = "NOR"
    XOR = "XOR"
    XNOR = "XNOR"

    @property
    def unary(self) -> bool:
        return self in (GateKind.BUF, GateKind.NOT)


class Gate(BaseModel):
    id: str
    kind: GateKind
    inputs: list[str] = Field(min_length=1)
    output: str

    @model_validator(mode="after")
    def _check_arity(self) -> Gate:
        if self.kind.unary and len(self.inputs) != 1:
            raise ValueError(f"{self.id}: {self.kind} requiere exactamente 1 entrada")
        if not self.kind.unary and len(self.inputs) < 2:
            raise ValueError(f"{self.id}: {self.kind} requiere al menos 2 entradas")
        return self


class Output(BaseModel):
    name: str
    net: str


class Netlist(BaseModel):
    name: str = "circuit"
    inputs: list[str]
    outputs: list[Output]
    gates: list[Gate]

    @model_validator(mode="after")
    def _check_structure(self) -> Netlist:
        drivers: dict[str, str] = {}

        def drive(net: str, by: str) -> None:
            if net in CONSTANT_NETS:
                raise ValueError(f"{by} no puede manejar la red constante {net}")
            if net in drivers:
                raise ValueError(f"red {net!r} manejada por {drivers[net]} y {by}")
            drivers[net] = by

        for name in self.inputs:
            drive(name, f"entrada {name}")
        ids = set()
        for g in self.gates:
            if g.id in ids:
                raise ValueError(f"id de compuerta repetido: {g.id}")
            ids.add(g.id)
            drive(g.output, g.id)

        for g in self.gates:
            for net in g.inputs:
                if net not in drivers and net not in CONSTANT_NETS:
                    raise ValueError(f"{g.id}: la red {net!r} no tiene quien la maneje")
        out_names = [o.name for o in self.outputs]
        if len(set(out_names)) != len(out_names):
            raise ValueError("nombres de salida repetidos")
        for o in self.outputs:
            if o.net not in drivers and o.net not in CONSTANT_NETS:
                raise ValueError(f"salida {o.name}: la red {o.net!r} no tiene quien la maneje")

        self.topological_order()
        return self

    def topological_order(self) -> list[Gate]:
        """Orden de evaluación; falla si hay lazos combinacionales."""
        by_output = {g.output: g for g in self.gates}
        state: dict[str, int] = {}  # 1 = visitando, 2 = terminado
        order: list[Gate] = []

        for root in self.gates:
            if root.id in state:
                continue
            stack: list[tuple[Gate, int]] = [(root, 0)]
            state[root.id] = 1
            while stack:
                g, i = stack.pop()
                if i < len(g.inputs):
                    stack.append((g, i + 1))
                    src = by_output.get(g.inputs[i])
                    if src is None:
                        continue
                    st = state.get(src.id)
                    if st == 1:
                        raise ValueError(f"lazo combinacional a través de {src.id}")
                    if st is None:
                        state[src.id] = 1
                        stack.append((src, 0))
                else:
                    state[g.id] = 2
                    order.append(g)
        return order

    def levels(self) -> dict[str, int]:
        """Nivel lógico de cada compuerta (entradas primarias = nivel 0)."""
        level: dict[str, int] = {n: 0 for n in self.inputs}
        level.update({c: 0 for c in CONSTANT_NETS})
        result: dict[str, int] = {}
        for g in self.topological_order():
            lv = 1 + max(level[n] for n in g.inputs)
            level[g.output] = lv
            result[g.id] = lv
        return result

    def depth(self) -> int:
        return max(self.levels().values(), default=0)
