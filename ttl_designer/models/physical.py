"""Netlist físico: el netlist mapeado más la asignación de compuertas a chips y pines.

Es el mismo grafo del netlist lógico mapeado (§NETLIST); este modelo solo añade
dónde vive cada compuerta y qué pines quedan fijos a Vcc o a GND.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, model_validator

from .netlist import CONSTANT_NETS, Netlist


class TieTarget(StrEnum):
    PULLUP = "pullup"  # a Vcc a través de resistencia (§MAPEO)
    GND = "gnd"


class TieReason(StrEnum):
    FIXED_INPUT = "entrada_fija"  # entrada de una compuerta usada, conectada a una constante
    FREE_GATE = "compuerta_libre"  # entrada de una compuerta que no se usa
    OPEN_COLLECTOR = "salida_colector_abierto"


class ChipInstance(BaseModel):
    ref: str
    part: str
    vcc_pin: int
    gnd_pin: int
    used_slots: list[str]
    free_slots: list[str]


class GatePlacement(BaseModel):
    gate_id: str
    ref: str
    slot: str
    input_pins: list[int]
    output_pin: int


class Tie(BaseModel):
    ref: str
    pin: int
    to: TieTarget
    reason: TieReason


class PhysicalDesign(BaseModel):
    netlist: Netlist
    chips: list[ChipInstance]
    placements: list[GatePlacement]
    ties: list[Tie]

    @model_validator(mode="after")
    def _check(self) -> PhysicalDesign:
        gate_ids = {g.id for g in self.netlist.gates}
        placed = [p.gate_id for p in self.placements]
        if sorted(placed) != sorted(gate_ids):
            raise ValueError("cada compuerta debe ubicarse exactamente una vez")
        slots = [(p.ref, p.slot) for p in self.placements]
        if len(set(slots)) != len(slots):
            raise ValueError("dos compuertas en el mismo lugar de un chip")
        refs = {c.ref for c in self.chips}
        if not {p.ref for p in self.placements} <= refs:
            raise ValueError("ubicación en un chip inexistente")
        return self

    @property
    def ic_count(self) -> int:
        return len(self.chips)

    def parts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for c in self.chips:
            out[c.part] = out.get(c.part, 0) + 1
        return dict(sorted(out.items()))

    def connections(self) -> dict[str, list[str]]:
        """Red → pines que conecta (``U1.3``); las constantes están en ``ties``."""
        gates = {g.id: g for g in self.netlist.gates}
        out: dict[str, list[str]] = {}
        for p in self.placements:
            g = gates[p.gate_id]
            for net, pin in zip(g.inputs, p.input_pins, strict=True):
                if net not in CONSTANT_NETS:  # las constantes van en `ties`
                    out.setdefault(net, []).append(f"{p.ref}.{pin}")
            out.setdefault(g.output, []).append(f"{p.ref}.{p.output_pin}")
        return out
