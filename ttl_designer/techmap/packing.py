"""Empaquetado: compuertas mapeadas → chips concretos, ranuras y pines (§MAPEO).

Antes de asignar se intenta vaciar el último chip de cada tipo reubicando sus
compuertas en ranuras sobrantes de otros chips ya presentes: un NOT en una NAND
libre con la otra entrada a pull-up, una NAND de 2 en una NAND de 3 libre, etc.
Cada reubicación preserva la función y reduce en uno el número de ICs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil

from ..models.catalog import OutputType
from ..models.netlist import CONST0, CONST1, Gate, GateKind, Netlist
from ..models.physical import (
    ChipInstance,
    GatePlacement,
    PhysicalDesign,
    Tie,
    TieReason,
    TieTarget,
)
from .cells import NEUTRAL, CellLibrary


@dataclass
class Rehost:
    gate_id: str
    from_part: str
    to_part: str


def _part_of(g: Gate, lib: CellLibrary) -> str:
    chip = lib.chip_for((g.kind, len(g.inputs)))
    if chip is None:
        raise ValueError(f"{g.id}: celda {g.kind}/{len(g.inputs)} no disponible")
    return chip.part


def _rehost_inputs(g: Gate, kind: GateKind, n: int) -> list[str] | None:
    """Entradas de ``g`` reescritas para una ranura (kind, n), o None si no cabe."""
    if g.kind is kind and not kind.unary and n >= len(g.inputs):
        return g.inputs + [NEUTRAL[kind]] * (n - len(g.inputs))
    if g.kind is GateKind.NOT and not kind.unary:
        x = g.inputs[0]
        if kind in (GateKind.NAND, GateKind.NOR):
            return [x] + [NEUTRAL[kind]] * (n - 1)
        if kind is GateKind.XOR and n == 2:
            return [x, CONST1]
        if kind is GateKind.XNOR and n == 2:
            return [x, CONST0]
    return None


def _order_key(levels: dict[str, int]) -> Callable[[Gate], tuple[int, int]]:
    """Orden estable: por nivel lógico y luego por número de compuerta."""
    return lambda g: (levels[g.id], int(g.id[1:]))


def absorb_spares(netlist: Netlist, lib: CellLibrary) -> tuple[Netlist, list[Rehost]]:
    gates = {g.id: g for g in netlist.gates}
    moves: list[Rehost] = []
    while True:
        by_part: dict[str, list[Gate]] = defaultdict(list)
        for g in gates.values():
            by_part[_part_of(g, lib)].append(g)
        gpp = {p: lib.chip(p).gates_per_package for p in by_part}
        spare = {p: ceil(len(gs) / gpp[p]) * gpp[p] - len(gs) for p, gs in by_part.items()}
        levels = Netlist(
            name=netlist.name,
            inputs=netlist.inputs,
            outputs=netlist.outputs,
            gates=list(gates.values()),
        ).levels()

        # compuertas que ocupan el último chip de cada tipo
        last_chip = {
            p: len(gs) - (ceil(len(gs) / gpp[p]) - 1) * gpp[p] for p, gs in by_part.items()
        }

        applied = False
        for part in sorted(by_part, key=lambda p: (last_chip[p], p)):
            victims = sorted(by_part[part], key=_order_key(levels))[-last_chip[part] :]
            room = {p: s for p, s in spare.items() if p != part and s > 0}
            plan: list[tuple[Gate, str, list[str]]] = []
            for v in victims:
                for host in sorted(room):
                    chip = lib.chip(host)
                    ins = _rehost_inputs(v, GateKind(chip.function.value), chip.inputs_per_gate)
                    if ins is not None and room[host] > 0:
                        plan.append((v, host, ins))
                        room[host] -= 1
                        break
                else:
                    break
            if len(plan) == len(victims):
                for v, host, ins in plan:
                    kind = GateKind(lib.chip(host).function.value)
                    gates[v.id] = Gate(id=v.id, kind=kind, inputs=ins, output=v.output)
                    moves.append(Rehost(v.id, part, host))
                applied = True
                break
        if not applied:
            break
    new = Netlist(
        name=netlist.name,
        inputs=netlist.inputs,
        outputs=netlist.outputs,
        gates=[gates[g.id] for g in netlist.gates],
    )
    return new, moves


def pack(netlist: Netlist, lib: CellLibrary) -> PhysicalDesign:
    levels = netlist.levels()
    by_part: dict[str, list[Gate]] = defaultdict(list)
    for g in netlist.gates:
        by_part[_part_of(g, lib)].append(g)

    chips: list[ChipInstance] = []
    placements: list[GatePlacement] = []
    ties: list[Tie] = []
    ref_n = 0
    for part in sorted(by_part, key=_part_sort_key):
        chip = lib.chip(part)
        kind = GateKind(chip.function.value)
        queue = sorted(by_part[part], key=_order_key(levels))
        for start in range(0, len(queue), chip.gates_per_package):
            ref_n += 1
            ref = f"U{ref_n}"
            batch: list[Gate | None] = list(queue[start : start + chip.gates_per_package])
            batch += [None] * (len(chip.gates) - len(batch))
            used: list[str] = []
            free: list[str] = []
            for slot, gate in zip(chip.gates, batch, strict=True):
                if gate is None:
                    free.append(slot.id)
                    target = TieTarget.PULLUP if NEUTRAL.get(kind) == CONST1 else TieTarget.GND
                    if kind is GateKind.NOT:
                        target = TieTarget.PULLUP
                    ties += [
                        Tie(ref=ref, pin=p, to=target, reason=TieReason.FREE_GATE)
                        for p in slot.inputs
                    ]
                    continue
                used.append(slot.id)
                placements.append(
                    GatePlacement(
                        gate_id=gate.id,
                        ref=ref,
                        slot=slot.id,
                        input_pins=slot.inputs,
                        output_pin=slot.output,
                    )
                )
                for net, pin in zip(gate.inputs, slot.inputs, strict=True):
                    if net in (CONST0, CONST1):
                        target = TieTarget.PULLUP if net == CONST1 else TieTarget.GND
                        ties.append(Tie(ref=ref, pin=pin, to=target, reason=TieReason.FIXED_INPUT))
                if chip.output_type is OutputType.OPEN_COLLECTOR:
                    ties.append(
                        Tie(
                            ref=ref,
                            pin=slot.output,
                            to=TieTarget.PULLUP,
                            reason=TieReason.OPEN_COLLECTOR,
                        )
                    )
            chips.append(
                ChipInstance(
                    ref=ref,
                    part=part,
                    vcc_pin=chip.power_pins.vcc,
                    gnd_pin=chip.power_pins.gnd,
                    used_slots=used,
                    free_slots=free,
                )
            )
    return PhysicalDesign(netlist=netlist, chips=chips, placements=placements, ties=ties)


def _part_sort_key(part: str) -> tuple[int, str]:
    digits = "".join(ch for ch in part if ch.isdigit())
    return (int(digits) if digits else 0, part)
